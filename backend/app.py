import os
import re
import math
import requests
from datetime import datetime
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
from google.genai import types

from supabase_client import (
    get_user_from_token,
    get_user_conversations,
    create_user_conversation,
    update_conversation_title,
    get_conversation_messages,
    save_chat_message,
    delete_user_conversation,
    search_pincode_db
)
from vector_search import search_documents
from calculator import (
    calculate_speed_post, calculate_ordinary_letter, calculate_postcard,
    calculate_inland_letter, calculate_ordinary_parcel, calculate_registered_post, calculate_insurance,
    calculate_sukanya_maturity, calculate_scss_payout, calculate_ppf_maturity,
    calculate_mis_payout, calculate_nsc_maturity, calculate_kvp_maturity
)

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("[AI Status] Gemini Client initialized: True")
    except Exception as e:
        print(f"[AI Status] Gemini Client initialization failed: {e}")
else:
    print("[AI Status] Gemini API Key missing!")

def get_auth_user():
    """Extracts and verifies Bearer token from request Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    return get_user_from_token(token)

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Dak Sahayak AI Backend (Supabase + Gemini)"})

# --- Conversation Endpoints ---

@app.route("/api/conversations", methods=["GET"])
def list_conversations():
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    conversations = get_user_conversations(user.id)
    return jsonify({"conversations": conversations})

@app.route("/api/conversations", methods=["POST"])
def create_conversation():
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    title = data.get("title", "New Chat").strip()
    conv_id = create_user_conversation(user.id, title=title)
    if not conv_id:
        return jsonify({"error": "Failed to create conversation"}), 500
    return jsonify({"conversation_id": conv_id, "title": title})

@app.route("/api/conversations/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    success = delete_user_conversation(conversation_id, user.id)
    return jsonify({"success": success})

@app.route("/api/conversations/<conversation_id>/messages", methods=["GET"])
def list_messages(conversation_id):
    user = get_auth_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    messages = get_conversation_messages(conversation_id)
    return jsonify({"messages": messages})

# --- Main Streaming Chat Endpoint with Supabase RAG ---

@app.route("/api/chat", methods=["POST"])
def chat():
    user = get_auth_user()
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    conversation_id = data.get("conversation_id", "").strip()
    language = data.get("language", "English").strip()
    pincode = data.get("pincode", "")
    user_location = data.get("user_location", {})

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    # Auto-create conversation if not provided
    if user and not conversation_id:
        conversation_id = create_user_conversation(user.id, title=user_message[:40])

    # Save user message to Supabase
    if conversation_id:
        save_chat_message(conversation_id, "user", user_message)

    # 1. Instant PIN Code Resolution
    pin_matches = re.findall(r'\b[1-9][0-9]{5}\b', user_message)
    if pin_matches:
        po_records = search_pincode_db(pin_matches[0])
        if po_records:
            po = po_records[0]
            pin_response = f"""**PIN Code Details**

* **PIN Code:** {po.get('Pincode', pin_matches[0])}
* **Post Office Name:** {po.get('Name', 'N/A')}
* **Office Type:** {po.get('BranchType', 'Sub Post Office')} ({po.get('DeliveryStatus', 'Delivery')})
* **Taluk:** {po.get('Taluk', 'N/A')}
* **District:** {po.get('District', 'N/A')}
* **Postal Division:** {po.get('Division', 'N/A')}
* **Postal Region:** {po.get('Region', 'N/A')}
* **Postal Circle:** {po.get('Circle', 'N/A')}
* **Head Office (HO):** {po.get('HeadOffice', 'N/A')}"""
            if conversation_id:
                save_chat_message(conversation_id, "assistant", pin_response)
            return Response(pin_response, content_type="text/plain; charset=utf-8")

    # 2. Fetch past conversation history from Supabase for multi-turn context
    history_turns = []
    if conversation_id:
        past_msgs = get_conversation_messages(conversation_id)
        # Exclude the very last user message that was just saved
        for m in past_msgs[:-1]:
            role = "user" if m.get("role") == "user" else "model"
            content = m.get("content", "")
            if content:
                history_turns.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content)]
                ))

    # 3. Supabase pgvector Semantic Search (Top 3 Chunks)
    retrieved_chunks = search_documents(user_message, top_k=3, match_threshold=0.25)
    context_text = ""
    if retrieved_chunks:
        blocks = [c["text"] for c in retrieved_chunks if c.get("text")]
        context_text = "\n\n---\n\n".join(blocks)

    location_str = f"\nUser Geolocation PIN Code: {pincode} ({user_location.get('suburb', '')}, {user_location.get('city', '')}, {user_location.get('state', '')})" if pincode else ""

    # Detect financial calculations
    calc_context = ""
    msg_lower = user_message.lower()
    amt_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b', msg_lower)
    raw_num_match = re.search(r'\b\d{4,7}\b', msg_lower)
    amt_val = None
    if amt_match:
        amt_val = float(amt_match.group(1)) * 100000.0
    elif raw_num_match:
        amt_val = float(raw_num_match.group(0))

    if amt_val:
        if any(k in msg_lower for k in ["sukanya", "ssa", "daughter", "girl"]):
            res = calculate_sukanya_maturity(amt_val)
            calc_context = f"\n\nCalculation Sukanya: Deposit ₹{res['annual_deposit']:,.2f}/yr | Total Invested ₹{res['total_invested']:,.2f} | Interest ₹{res['interest_earned']:,.2f} | Maturity ₹{res['maturity_value']:,.2f}"
        elif any(k in msg_lower for k in ["scss", "senior citizen", "senior"]):
            res = calculate_scss_payout(amt_val)
            calc_context = f"\n\nCalculation SCSS: Deposit ₹{res['deposit_amount']:,.2f} | Quarterly Payout ₹{res['quarterly_payout']:,.2f} | Total Interest ₹{res['total_interest_earned']:,.2f}"
        elif any(k in msg_lower for k in ["ppf", "provident"]):
            res = calculate_ppf_maturity(amt_val)
            calc_context = f"\n\nCalculation PPF: Annual Deposit ₹{res['annual_deposit']:,.2f} | Total Invested ₹{res['total_invested']:,.2f} | Maturity ₹{res['maturity_value']:,.2f}"
        elif any(k in msg_lower for k in ["mis", "monthly income"]):
            res = calculate_mis_payout(amt_val)
            calc_context = f"\n\nCalculation MIS: Deposit ₹{res['deposit_amount']:,.2f} | Monthly Income ₹{res['monthly_payout']:,.2f}"

    system_prompt = f"""You are Dak Sahayak (डाक सहायक), the official India Post AI assistant.
Respond strictly and fluently in {language}. If the language is a regional Indian language (e.g. Hindi, Kannada, Tamil, Telugu, Marathi, Bengali), generate natural native script text.
Always provide structured, clear answers for Post Office Small Savings Schemes, POSB Banking charges, Mail/Speed Post rates, and Services.

Official India Post Small Savings Rates:
- Sukanya Samriddhi Account (SSA): 8.2% p.a. (Compounded annually)
- Senior Citizen Savings Scheme (SCSS): 8.2% p.a. (Paid quarterly)
- National Savings Certificate (NSC VIII): 7.7% p.a. (Compounded annually)
- Kisan Vikas Patra (KVP): 7.5% p.a. (Doubles in 115 months / 9 yrs 7 mos)
- Mahila Samman Savings Certificate (MSSC): 7.5% p.a. (Compounded quarterly)
- Post Office Time Deposit (5-Year FD): 7.5% p.a. (1-Yr 6.9%, 2-Yr 7.0%, 3-Yr 7.1%)
- Post Office Monthly Income Scheme (MIS): 7.4% p.a. (Paid monthly)
- Public Provident Fund (PPF): 7.1% p.a. (Compounded annually)
- Post Office Recurring Deposit (RD): 6.7% p.a. (Compounded quarterly)
- Post Office Savings Account (POSA): 4.0% p.a.

Official India Post Bank Fee Schedule:
- Duplicate Passbook: ₹50
- Statement of Account / Deposit Receipt: ₹20 per case
- Passbook in lieu of lost/mutilated certificate: ₹10 per registration
- Nomination change / cancellation: Completely Free (No fee applicable as per SB Order No. 05/2025)
- Account Transfer: ₹100
- Pledging of Account: ₹100
- Cheque Book: Free for up to 10 leaves/year, ₹2 per leaf thereafter
- Cheque Dishonour / Bounce: ₹100

{location_str}
{calc_context}

Official India Post Knowledge Base (from Supabase Vector DB):
{context_text}"""

    def generate_stream():
        full_text = ""
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        stream_success = False

        if client:
            for m in models_to_try:
                try:
                    chat_session = client.chats.create(
                        model=m,
                        history=history_turns,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.2
                        )
                    )
                    response_stream = chat_session.send_message_stream(user_message)
                    for chunk in response_stream:
                        if chunk and chunk.text:
                            full_text += chunk.text
                            yield chunk.text
                    if full_text.strip():
                        stream_success = True
                        break
                except Exception as ex:
                    try:
                        response_stream = client.models.generate_content_stream(
                            model=m,
                            contents=f"System Prompt:\n{system_prompt}\n\nQuestion: {user_message}",
                            config=types.GenerateContentConfig(temperature=0.2)
                        )
                        for chunk in response_stream:
                            if chunk and chunk.text:
                                full_text += chunk.text
                                yield chunk.text
                        if full_text.strip():
                            stream_success = True
                            break
                    except Exception as ex2:
                        print(f"[-] Streaming error with {m}: {ex2}")

        if not stream_success or not full_text.strip():
            full_text = "India Post provides comprehensive Small Savings, Mail, and POSB Banking services across India."
            yield full_text

        # Save assistant response to Supabase messages table
        if conversation_id:
            save_chat_message(conversation_id, "assistant", full_text)
            # Update title on first turn
            if len(history_turns) == 0:
                update_conversation_title(conversation_id, user_message[:45])

    return Response(stream_with_context(generate_stream()), content_type="text/plain; charset=utf-8")

# --- Calculator & PIN Endpoints ---

@app.route("/api/calculator", methods=["POST"])
def api_calculator():
    data = request.get_json() or {}
    service = str(data.get("service", "speed_post")).lower().strip()
    weight = data.get("weight", 50)
    distance = data.get("distance", "local")

    if "letter" in service:
        res = calculate_ordinary_letter(weight)
    elif "postcard" in service:
        res = calculate_postcard(data.get("card_type", "single"))
    elif "parcel" in service and "speed" not in service:
        res = calculate_ordinary_parcel(weight)
    elif "registered" in service:
        res = calculate_registered_post(postage_base=float(data.get("postage", 5.0)), ad_required=bool(data.get("ad_card", False)))
    elif "insurance" in service:
        res = calculate_insurance(data.get("insured_value", 200))
    elif "sukanya" in service:
        res = calculate_sukanya_maturity(float(data.get("annual_deposit", 10000)))
    elif "ppf" in service:
        res = calculate_ppf_maturity(float(data.get("annual_deposit", 10000)))
    elif "scss" in service:
        res = calculate_scss_payout(float(data.get("deposit_amount", 100000)))
    elif "mis" in service:
        res = calculate_mis_payout(float(data.get("deposit_amount", 100000)))
    elif "nsc" in service:
        res = calculate_nsc_maturity(float(data.get("deposit_amount", 10000)))
    elif "kvp" in service:
        res = calculate_kvp_maturity(float(data.get("deposit_amount", 10000)))
    else:
        res = calculate_speed_post(weight, distance)

    return jsonify(res)

@app.route("/api/pincode/<query>", methods=["GET"])
def api_pincode(query):
    query_str = str(query).strip()
    results = search_pincode_db(query_str)
    if results:
        return jsonify({"status": "Success", "results": results})
    return jsonify({"status": "Error", "message": f"No post office found for '{query_str}'"}), 404

@app.route("/api/reverse-pincode", methods=["GET"])
def api_reverse_pincode():
    lat = request.args.get("lat", "").strip()
    lon = request.args.get("lon", "").strip()

    if not lat or not lon:
        return jsonify({"status": "Error", "message": "Latitude and longitude required"}), 400

    headers = {"User-Agent": "DakSahayakApp/2.0 (India Post AI Assistant)"}
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"

    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            res_json = resp.json()
            address = res_json.get("address", {})
            postcode = address.get("postcode", "").strip()
            if postcode:
                postcode_match = re.search(r'\b[1-9][0-9]{5}\b', postcode)
                if postcode_match:
                    postcode = postcode_match.group(0)

            if postcode and len(postcode) == 6:
                results = search_pincode_db(postcode)
                return jsonify({
                    "status": "Success",
                    "pincode": postcode,
                    "address": address,
                    "results": results
                })
    except Exception as e:
        print(f"[-] Reverse geocoding error: {e}")

    return jsonify({
        "status": "Fallback",
        "message": "Unable to resolve location to a valid 6-digit PIN. Please enter your PIN manually."
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
