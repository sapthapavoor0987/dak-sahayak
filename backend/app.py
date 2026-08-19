import os
import re
import math
import base64
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from dotenv import load_dotenv
from google import genai
from google.genai import types
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from fetch_sources import harvest_documents
from pdf_reader import load_dynamic_knowledge_base
from database import init_db, log_chat, update_feedback, get_recent_history, search_pincode
from calculator import (
    calculate_speed_post, calculate_ordinary_letter, calculate_postcard,
    calculate_inland_letter, calculate_ordinary_parcel, calculate_registered_post, calculate_insurance,
    calculate_sukanya_maturity, calculate_scss_payout, calculate_ppf_maturity,
    calculate_mis_payout, calculate_nsc_maturity, calculate_kvp_maturity
)

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    if os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")

# Initialize Database
init_db()

# Load environment variables explicitly
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(dotenv_path)

# Initialize Gemini Client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print(f"[AI Status] Gemini Client initialized: True")
    except Exception as e:
        print(f"[AI Status] Gemini Client initialized: False ({e})")
else:
    print("[AI Status] Gemini Client initialized: False")

# RAG Index State
KNOWLEDGE_CHUNKS = []
VECTORIZER = None
CHUNK_MATRIX = None

def init_rag_system():
    """Builds TF-IDF vector index over dynamic document chunks in data/docs."""
    global KNOWLEDGE_CHUNKS, VECTORIZER, CHUNK_MATRIX
    
    # Ensure documents are harvested
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "docs")
    if not os.path.exists(docs_dir) or not os.listdir(docs_dir):
        harvest_documents()

    KNOWLEDGE_CHUNKS = load_dynamic_knowledge_base(docs_dir)
    if KNOWLEDGE_CHUNKS:
        texts = [chunk["text"] for chunk in KNOWLEDGE_CHUNKS]
        VECTORIZER = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        CHUNK_MATRIX = VECTORIZER.fit_transform(texts)
        print(f"[*] RAG Engine initialized: {len(KNOWLEDGE_CHUNKS)} document chunks indexed.")
    else:
        print("[!] Warning: Knowledge base is empty.")

def retrieve_top_chunks(query, top_k=2):
    """Retrieves top_k relevant text chunks matching query via TF-IDF cosine similarity."""
    global KNOWLEDGE_CHUNKS, VECTORIZER, CHUNK_MATRIX
    if not KNOWLEDGE_CHUNKS or VECTORIZER is None or CHUNK_MATRIX is None:
        return []

    try:
        query_vec = VECTORIZER.transform([query])
        similarities = cosine_similarity(query_vec, CHUNK_MATRIX).flatten()
        top_indices = similarities.argsort()[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0.01:
                chunk = KNOWLEDGE_CHUNKS[idx]
                results.append({
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "page": chunk["page"],
                    "source_display": chunk["source_display"],
                    "score": round(score, 4)
                })
        return results
    except Exception as e:
        print(f"[-] Vector search error: {e}")
        return []

def clean_chunk_text(text):
    """Strips URLs, metadata headers, and raw website noise from context text."""
    if not text:
        return ""
    cleaned = re.sub(r'https?://\S+|www\.\S+', '', text)
    cleaned = re.sub(r'(?i)^(source url|source|url|file|page):.*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'(?i)\b(overview|detail|summary|feature):\s*', '', cleaned)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return "\n".join(lines)

# Initialize RAG on startup
init_rag_system()

# Initialize Persistent ChromaDB Vector Search Engine
import chromadb
from ingest_chroma import ingest_postal_knowledge

CHROMA_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_data")
chroma_client = None
chroma_collection = None

def init_chroma_system():
    global chroma_client, chroma_collection
    try:
        if not os.path.exists(CHROMA_DATA_PATH):
            ingest_postal_knowledge()
            
        chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
        chroma_collection = chroma_client.get_or_create_collection(
            name="postal_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"[*] Persistent ChromaDB Client initialized at '{CHROMA_DATA_PATH}' (Collection: 'postal_knowledge', Documents: {chroma_collection.count()}).")
    except Exception as e:
        print(f"[-] Error initializing persistent ChromaDB: {e}")

init_chroma_system()

def query_chroma_knowledge(query_text: str, top_k: int = 2):
    """Queries persistent ChromaDB collection for semantic vector matches."""
    if not chroma_collection:
        return []
    try:
        results = chroma_collection.query(
            query_texts=[query_text],
            n_results=top_k
        )
        retrieved_docs = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results.get("metadatas", [[]])[0]
            for idx, doc in enumerate(docs):
                meta = metas[idx] if idx < len(metas) else {}
                retrieved_docs.append({
                    "text": doc,
                    "metadata": meta,
                    "source": meta.get("source", "ChromaDB"),
                    "source_display": meta.get("scheme_name", meta.get("service", "Chroma Vector DB"))
                })
        return retrieved_docs
    except Exception as ex:
        print(f"[-] Semantic Chroma vector query error: {ex}")
        return []

# PIN Code Lookup Mock Database fallback for offline resilience
MOCK_PINCODES = {
    "110001": [
        {"Name": "New Delhi GPO", "BranchType": "Head Post Office", "DeliveryStatus": "Delivery", "District": "New Delhi", "State": "Delhi", "Pincode": "110001"},
        {"Name": "Connaught Place SO", "BranchType": "Sub Post Office", "DeliveryStatus": "Non-Delivery", "District": "New Delhi", "State": "Delhi", "Pincode": "110001"}
    ],
    "400001": [
        {"Name": "Mumbai GPO", "BranchType": "Head Post Office", "DeliveryStatus": "Delivery", "District": "Mumbai", "State": "Maharashtra", "Pincode": "400001"},
        {"Name": "Fort Market SO", "BranchType": "Sub Post Office", "DeliveryStatus": "Delivery", "District": "Mumbai", "State": "Maharashtra", "Pincode": "400001"}
    ],
    "560001": [
        {"Name": "Bengaluru GPO", "BranchType": "Head Post Office", "DeliveryStatus": "Delivery", "District": "Bengaluru", "State": "Karnataka", "Pincode": "560001"},
        {"Name": "Vidhana Soudha SO", "BranchType": "Sub Post Office", "DeliveryStatus": "Delivery", "District": "Bengaluru", "State": "Karnataka", "Pincode": "560001"}
    ],
    "700001": [
        {"Name": "Kolkata GPO", "BranchType": "Head Post Office", "DeliveryStatus": "Delivery", "District": "Kolkata", "State": "West Bengal", "Pincode": "700001"}
    ],
    "600001": [
        {"Name": "Chennai GPO", "BranchType": "Head Post Office", "DeliveryStatus": "Delivery", "District": "Chennai", "State": "Tamil Nadu", "Pincode": "600001"}
    ]
}

def get_real_pincode_details(pincode: str):
    p_clean = pincode.strip()
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(f"https://api.postalpincode.in/pincode/{p_clean}", headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data and isinstance(data, list) and data[0].get("Status") == "Success":
                po_list = data[0].get("PostOffice", [])
                if po_list:
                    primary = po_list[0]
                    # Format exact details
                    po_names = ", ".join([f"{p['Name']} ({p.get('BranchType', 'PO')})" for p in po_list])
                    formatted = (
                        f"**PIN Code Details**\n\n"
                        f"* **PIN Code:** {primary.get('Pincode', p_clean)}\n"
                        f"* **Post Office Name:** {po_names}\n"
                        f"* **Office Type:** {primary.get('BranchType', 'Sub Post Office')} ({primary.get('DeliveryStatus', 'Delivery Office')})\n"
                        f"* **Taluk:** {primary.get('Block') or primary.get('Taluk') or primary.get('District')}\n"
                        f"* **District:** {primary.get('District')}\n"
                        f"* **Postal Division:** {primary.get('Division')}\n"
                        f"* **Postal Region:** {primary.get('Region')}\n"
                        f"* **Postal Circle:** {primary.get('Circle')}\n"
                        f"* **State:** {primary.get('State')}"
                    )
                    return formatted
    except Exception as e:
        print(f"Error fetching PIN: {e}")

    # Fallback to local DB search if online API unavailable
    try:
        local_records = search_pincode(p_clean)
        if local_records:
            primary = local_records[0]
            po_names = ", ".join([f"{p['Name']} ({p.get('BranchType', 'PO')})" for p in local_records])
            formatted = (
                f"**PIN Code Details**\n\n"
                f"* **PIN Code:** {primary.get('Pincode', p_clean)}\n"
                f"* **Post Office Name:** {po_names}\n"
                f"* **Office Type:** {primary.get('BranchType', 'Sub Post Office')} ({primary.get('DeliveryStatus', 'Delivery Office')})\n"
                f"* **Taluk:** {primary.get('Taluk') or primary.get('District')}\n"
                f"* **District:** {primary.get('District')}\n"
                f"* **Postal Division:** {primary.get('Division')}\n"
                f"* **Postal Region:** {primary.get('Region')}\n"
                f"* **Postal Circle:** {primary.get('Circle')}\n"
                f"* **State:** {primary.get('State')}"
            )
            return formatted
    except Exception as ex:
        print(f"Local PIN lookup error: {ex}")

    return None

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    language = data.get("language", "English").strip()
    history_raw = data.get("history", [])
    pincode = data.get("pincode", "")
    user_location = data.get("user_location", {})

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    def generate_stream():
        # 0. Instant PIN Code Resolution (6-digit Indian PIN match)
        pin_matches = re.findall(r'\b[1-9][0-9]{5}\b', user_message)
        if pin_matches:
            real_pincode_response = get_real_pincode_details(pin_matches[0])
            if real_pincode_response:
                log_chat(user_message, real_pincode_response, matched_category="PIN Code Lookup")
                yield real_pincode_response
                return

        # Clean and format incoming history turns
        formatted_history = []
        history_context_keywords = []

        if isinstance(history_raw, list):
            turns = history_raw[:-1] if (history_raw and history_raw[-1].get("role") == "user" and history_raw[-1].get("parts") and history_raw[-1]["parts"][0] == user_message) else history_raw
            
            for turn in turns:
                role = turn.get("role", "")
                parts = turn.get("parts", [])
                text_content = ""
                if isinstance(parts, list) and parts:
                    text_content = str(parts[0])
                elif isinstance(turn.get("content"), str):
                    text_content = turn.get("content")

                if role in ["user", "model"] and text_content.strip():
                    formatted_history.append(types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=text_content.strip())]
                    ))
                    words = [w for w in text_content.split() if len(w) > 3 and w.lower() not in ["what", "how", "where", "when", "tell", "details", "scheme", "post", "office", "avail", "apply", "please", "can", "with"]]
                    history_context_keywords.extend(words[:3])

        # 1. Reduced Top 2 Semantic Vector Search via ChromaDB & Dynamic RAG (Immediate Latency Fix)
        rag_query = f"{' '.join(list(set(history_context_keywords))[-4:])} {user_message}".strip()
        chroma_chunks = query_chroma_knowledge(rag_query, top_k=2)
        retrieved_chunks = retrieve_top_chunks(rag_query, top_k=2)
        
        all_chunks = chroma_chunks + retrieved_chunks
        context_text = ""
        if all_chunks:
            context_blocks = [clean_chunk_text(chunk['text']) for chunk in all_chunks[:2]]
            context_text = "\n\n".join([b for b in context_blocks if b])

        location_str = f"\nUser Geolocation PIN Code: {pincode} ({user_location.get('suburb', '')}, {user_location.get('city', '')}, {user_location.get('state', '')})" if pincode else ""

        detected_pin_context = ""
        if pin_matches:
            pin_blocks = []
            for p_code in set(pin_matches):
                po_records = search_pincode(p_code)
                if po_records:
                    for po in po_records[:2]:
                        block = f"* PIN: {po.get('Pincode', p_code)} | Office: {po.get('Name', 'N/A')} ({po.get('BranchType', 'SO')}) | District: {po.get('District', 'N/A')}, {po.get('State', 'N/A')}"
                        pin_blocks.append(block.strip())
            if pin_blocks:
                detected_pin_context = "\n\nPIN Directory:\n" + "\n".join(pin_blocks)

        amt_val = None
        raw_num_match = re.search(r'\b(?:rs\.?|inr|₹)?\s*([0-9,]+(?:\.[0-9]+)?)\b', user_message.lower())
        if raw_num_match:
            try:
                raw_str = raw_num_match.group(1).replace(',', '')
                if raw_str and float(raw_str) >= 100:
                    amt_val = float(raw_str)
            except Exception:
                pass

        calc_context = ""
        msg_lower = user_message.lower()
        if amt_val:
            if any(k in msg_lower for k in ["sukanya", "ssa", "daughter", "girl"]):
                res = calculate_sukanya_maturity(amt_val)
                calc_context = f"\n\nCalculation Sukanya: Deposit ₹{res['annual_deposit']:,.2f}/yr | Invested ₹{res['total_invested']:,.2f} | Interest ₹{res['interest_earned']:,.2f} | Maturity ₹{res['maturity_value']:,.2f}"
            elif any(k in msg_lower for k in ["scss", "senior citizen", "senior"]):
                res = calculate_scss_payout(amt_val)
                calc_context = f"\n\nCalculation SCSS: Deposit ₹{res['deposit_amount']:,.2f} | Quarterly Payout ₹{res['quarterly_payout']:,.2f} | Total Interest ₹{res['total_interest_earned']:,.2f}"
            elif any(k in msg_lower for k in ["ppf", "provident"]):
                res = calculate_ppf_maturity(amt_val)
                calc_context = f"\n\nCalculation PPF: Annual Deposit ₹{res['annual_deposit']:,.2f} | Invested ₹{res['total_invested']:,.2f} | Maturity ₹{res['maturity_value']:,.2f}"
            elif any(k in msg_lower for k in ["mis", "monthly income"]):
                res = calculate_mis_payout(amt_val)
                calc_context = f"\n\nCalculation MIS: Deposit ₹{res['deposit_amount']:,.2f} | Monthly Income ₹{res['monthly_payout']:,.2f}"

        system_prompt = f"""You are Dak Sahayak (डाक सहायक), official India Post AI assistant. Provide structured, factual answers for all Post Office Small Savings Schemes, POSB Banking, Mail/Speed Post rates, and Services.
Respond strictly and fluently in {language}. Keep system instructions tight and direct.

Small Savings Rates: SSA 8.2%, SCSS 8.2%, NSC 7.7%, KVP 7.5%, MSSC 7.5%, 5-Yr FD 7.5%, MIS 7.4%, PPF 7.1%, RD 6.7%, POSA 4.0%.
Fee Schedule: Duplicate Passbook ₹50, Account Transfer ₹100, Nomination Free (SB Order 05/2025).

{location_str}
{detected_pin_context}
{calc_context}

Official India Post Knowledge:
{context_text}"""

        full_response_text = ""
        stream_success = False

        if client:
            models_to_try = ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash", "gemini-flash-latest"]
            for m in models_to_try:
                try:
                    chat = client.chats.create(
                        model=m,
                        history=formatted_history,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.2
                        )
                    )
                    response_stream = chat.send_message_stream(user_message)
                    for chunk in response_stream:
                        if chunk and chunk.text:
                            full_response_text += chunk.text
                            yield chunk.text
                    if full_response_text.strip():
                        stream_success = True
                        break
                except Exception as ex:
                    try:
                        response_stream = client.models.generate_content_stream(
                            model=m,
                            contents=f"System Prompt:\n{system_prompt}\n\nPrevious Conversation:\n{formatted_history}\n\nCurrent Question: {user_message}",
                            config=types.GenerateContentConfig(
                                temperature=0.2
                            )
                        )
                        for chunk in response_stream:
                            if chunk and chunk.text:
                                full_response_text += chunk.text
                                yield chunk.text
                        if full_response_text.strip():
                            stream_success = True
                            break
                    except Exception as ex2:
                        print(f"[-] Streaming error with {m}: {ex2}")

        # Fallback if streaming failed or client empty
        if not stream_success or not full_response_text.strip():
            if retrieved_chunks:
                blocks = []
                for idx, chunk in enumerate(retrieved_chunks[:2], 1):
                    clean_t = clean_chunk_text(chunk.get("text", ""))
                    if clean_t:
                        clean_lines = [l.strip() for l in clean_t.splitlines() if l.strip() and not l.strip().startswith("---")]
                        formatted_block = "\n".join([f"* {l}" if not l.startswith("*") and not l.startswith("#") else l for l in clean_lines[:4]])
                        doc_title = chunk.get("source_display", f"Information {idx}")
                        blocks.append(f"### {idx}. {doc_title}\n{formatted_block}")
                full_response_text = "\n\n---\n\n".join(blocks) if blocks else "India Post provides comprehensive Small Savings, Mail, and POSB Banking services across India."
            else:
                full_response_text = "India Post provides comprehensive Small Savings, Mail, and POSB Banking services across India."
            yield full_response_text

        # Log conversation to SQLite database
        category = "General Inquiry"
        if "speed" in msg_lower or "tariff" in msg_lower or "rate" in msg_lower or "parcel" in msg_lower:
            category = "Speed Post & Mails"
        elif "saving" in msg_lower or "ppf" in msg_lower or "sukanya" in msg_lower or "deposit" in msg_lower:
            category = "Post Office Savings Bank"
        log_chat(user_message, full_response_text, matched_category=category)

    return Response(stream_with_context(generate_stream()), content_type="text/plain; charset=utf-8")

@app.route("/api/history", methods=["GET"])
def api_history():
    history = get_recent_history(limit=50)
    return jsonify({"history": history})

@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json() or {}
    log_id = data.get("log_id")
    feedback = data.get("feedback")

    if not log_id or feedback not in ["positive", "negative"]:
        return jsonify({"error": "Invalid log_id or feedback parameter"}), 400

    success = update_feedback(log_id, feedback)
    return jsonify({"success": success, "log_id": log_id, "feedback": feedback})

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
    else:
        res = calculate_speed_post(weight, distance)

    return jsonify(res)

@app.route("/api/pincode/<query>", methods=["GET"])
def api_pincode(query):
    query_str = str(query).strip()
    results = search_pincode(query_str)
    if results:
        return jsonify({"status": "Success", "results": results})
    return jsonify({"status": "Error", "message": f"No post office found for '{query_str}'"}), 404

@app.route("/api/reverse-pincode", methods=["GET"])
def api_reverse_pincode():
    lat = request.args.get("lat", "").strip()
    lon = request.args.get("lon", "").strip()

    if not lat or not lon:
        return jsonify({"status": "Error", "message": "Latitude and longitude query parameters are required."}), 400

    headers = {"User-Agent": "DakSahayakApp/1.0 (India Post AI Assistant)"}
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
                results = search_pincode(postcode)
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
    app.run(host="127.0.0.1", port=5000, debug=False)
