import os
import re
import math
import base64
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
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
    calculate_inland_letter, calculate_ordinary_parcel, calculate_registered_post, calculate_insurance
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Initialize Database
init_db()

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

def retrieve_top_chunks(query, top_k=3):
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

# Web Routes
@app.route("/")
def index():
    return render_template("index.html")

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

    # Clean and format incoming history turns
    formatted_history = []
    history_context_keywords = []

    if isinstance(history_raw, list):
        # Exclude the very last entry if client pushed user_message before making fetch
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
                # Extract key nouns/topics for contextual RAG retrieval
                words = [w for w in text_content.split() if len(w) > 3 and w.lower() not in ["what", "how", "where", "when", "tell", "details", "scheme", "post", "office", "avail", "apply", "please", "can", "with"]]
                history_context_keywords.extend(words[:3])

    # 1. Dynamic Context Retrieval via RAG (Combines history context with current query)
    rag_query = f"{' '.join(list(set(history_context_keywords))[-6:])} {user_message}".strip()
    retrieved_chunks = retrieve_top_chunks(rag_query, top_k=5)
    
    context_text = ""
    sources_list = []
    if retrieved_chunks:
        context_blocks = [clean_chunk_text(chunk['text']) for chunk in retrieved_chunks]
        context_text = "\n".join([b for b in context_blocks if b])
        sources_list = retrieved_chunks

    location_str = f"\nUser Geolocation PIN Code: {pincode} ({user_location.get('suburb', '')}, {user_location.get('city', '')}, {user_location.get('state', '')})" if pincode else ""

    # Detect 6-digit Indian PIN codes in message
    pin_matches = re.findall(r'\b[1-9][0-9]{5}\b', user_message)
    detected_pin_context = ""
    if pin_matches:
        pin_blocks = []
        for p_code in set(pin_matches):
            po_records = search_pincode(p_code)
            if po_records:
                first_po = po_records[0]
                state_dist = f"**State & District:** {first_po.get('State', 'N/A')}, {first_po.get('District', 'N/A')}"
                taluk_div = f"**Taluk / Division:** {first_po.get('Taluk', 'N/A')}, {first_po.get('Division', 'N/A')}"
                
                office_bullets = []
                for po in po_records:
                    office_bullets.append(f"  * {po.get('Name')} — Type: {po.get('BranchType')} | Delivery Status: {po.get('DeliveryStatus')}")
                
                block = f"### Geographic & Branch Resolution for PIN Code {p_code}:\n- {state_dist}\n- {taluk_div}\n- **Covered Post Offices & Branch Types:**\n" + "\n".join(office_bullets)
                pin_blocks.append(block)

        if pin_blocks:
            detected_pin_context = "\n\n" + "\n\n".join(pin_blocks)

    system_prompt = f"""You are Dak Sahayak (डाक सहायक), the official India Post AI assistant.
Respond strictly and fluently in {language}. If the language is a regional Indian language (e.g. Hindi, Kannada, Tamil, Telugu, Marathi, Bengali), generate natural native script text.
Always maintain strict conversational continuity with previous turns in this dialogue session.
Whenever the user asks about a PIN code or its location/taluk/district/branch, always provide the exact District, Taluk/Tehsil, Postal Division, and an itemized breakdown of all Sub-Offices (SO) and Branch Offices (BO) under that PIN code.
When the user asks follow-up questions (such as 'when will it reach?', 'minimum amount?', 'how to apply?', 'what if 2kg?', 'how to withdraw early?'), answer specifically for the exact scheme, consignment, or service previously discussed without asking them to repeat details.
Format your response in clear, informative bullet points.
{location_str}
{detected_pin_context}

Official India Post Knowledge Base:
{context_text}"""

    reply_text = ""
    if client:
        models_to_try = ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-latest"]
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
                response = chat.send_message(user_message)
                if response and response.text:
                    reply_text = response.text.strip()
                    break
            except Exception as ex:
                try:
                    response = client.models.generate_content(
                        model=m,
                        contents=f"Previous Conversation:\n{formatted_history}\n\nCurrent Question: {user_message}",
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.2
                        )
                    )
                    if response and response.text:
                        reply_text = response.text.strip()
                        break
                except Exception as ex2:
                    print(f"[-] Chat model {m} note: {ex2}")

    # Fallback if reply_text is empty
    if not reply_text:
        if retrieved_chunks:
            extracted_bullets = []
            for chunk in retrieved_chunks:
                text_content = chunk.get('text', '')
                for raw_line in text_content.splitlines():
                    clean_line = raw_line.strip().lstrip('*-•1234567890. ')
                    if len(clean_line) > 25 and not clean_line.lower().startswith("source"):
                        extracted_bullets.append(f"* {clean_line}")
                    if len(extracted_bullets) >= 4:
                        break
                if len(extracted_bullets) >= 4:
                    break
            reply_text = "\n".join(extracted_bullets[:4]) if extracted_bullets else "* India Post provides comprehensive Mail, Savings Bank, and Insurance services across India."
        else:
            reply_text = "* India Post provides comprehensive Mail, Savings Bank, and Insurance services across India."

    # Determine category
    category = "General Inquiry"
    msg_lower = user_message.lower()
    if "speed" in msg_lower or "tariff" in msg_lower or "rate" in msg_lower or "parcel" in msg_lower or "mail" in msg_lower or "tracking" in msg_lower:
        category = "Speed Post & Mails"
    elif "saving" in msg_lower or "ppf" in msg_lower or "sukanya" in msg_lower or "deposit" in msg_lower or "account" in msg_lower or "pomis" in msg_lower or "kvp" in msg_lower or "nsc" in msg_lower or "rd" in msg_lower or "td" in msg_lower:
        category = "Post Office Savings Bank"
    elif "pli" in msg_lower or "rpli" in msg_lower or "insurance" in msg_lower or "suraksha" in msg_lower or "santosh" in msg_lower:
        category = "Postal Life Insurance"
    elif "ippb" in msg_lower or "aadhaar" in msg_lower or "aeps" in msg_lower or "doorstep" in msg_lower or "passport" in msg_lower:
        category = "IPPB & Aadhaar Services"
    elif "complaint" in msg_lower or "grievance" in msg_lower or "timing" in msg_lower or "hours" in msg_lower or "charter" in msg_lower or "compensation" in msg_lower:
        category = "Grievance & Facilities"

    log_id = log_chat(user_message, reply_text, matched_category=category)

    return jsonify({
        "reply": reply_text,
        "response": reply_text,
        "sources": [],
        "log_id": log_id,
        "category": category
    })

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

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
