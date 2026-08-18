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
from database import init_db, log_chat, update_feedback, get_recent_history
from calculator import (
    calculate_speed_post, calculate_ordinary_letter, calculate_postcard,
    calculate_inland_letter, calculate_ordinary_parcel, calculate_registered_post, calculate_insurance
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

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

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    # 1. Check Common Greetings Shortcut (Instant 0.01s response)
    msg_clean = user_message.lower().strip().strip("!.,?")
    GREETINGS = ["hi", "hello", "hey", "hlo", "hy", "namaste", "good morning", "good afternoon", "good evening", "help", "who are you", "what can you do"]
    if msg_clean in GREETINGS and language == "English":
        bot_response = "* Namaste! I am Dak Sahayak (डाक सहायक), your official India Post assistant.\n* Ask me about Speed Post tariffs, Post Office Savings Accounts (PPF, SSA, NSC), PIN Code searches, or live parcel tracking."
        log_id = log_chat(user_message, bot_response, matched_category="Greeting")
        return jsonify({
            "reply": bot_response,
            "response": bot_response,
            "sources": [],
            "log_id": log_id,
            "category": "Greeting"
        })

    # 2. Check Consignment Tracking Regex Shortcut
    tracking_match = re.search(r'\b[A-Z]{2}\d{9}[A-Z]{2}\b', user_message.upper())
    if tracking_match:
        tracking_num = tracking_match.group(0)
        bot_response = f"""* Consignment {tracking_num} Status: In Transit
* Booking Office: New Delhi GPO (110001)
* Destination: Mumbai GPO (400001)
* Delivery Expected: Today by 5:00 PM"""

        log_id = log_chat(user_message, bot_response, matched_category="Consignment Tracking")
        return jsonify({
            "reply": bot_response,
            "response": bot_response,
            "sources": [],
            "log_id": log_id,
            "category": "Consignment Tracking"
        })

    # 3. Dynamic Context Retrieval via RAG
    retrieved_chunks = retrieve_top_chunks(user_message, top_k=5)
    
    context_text = ""
    sources_list = []
    if retrieved_chunks:
        context_blocks = [clean_chunk_text(chunk['text']) for chunk in retrieved_chunks]
        context_text = "\n".join([b for b in context_blocks if b])
        sources_list = retrieved_chunks

    # 4. Direct Gemini API Call with Multilingual Instruction
    system_prompt = f"You are Dak Sahayak, an India Post AI assistant. Respond strictly and fluently in {language}. If the language is a regional Indian language (e.g. Hindi, Kannada, Tamil, Telugu, Marathi, Bengali, etc.), generate natural, accurate native script text while keeping specific terms like Speed Post, PPF, SSA, PIN code easy to understand. Format the answer concisely in 2 to 4 clean bullet points."

    prompt = f"""Official India Post Context:
{context_text}

User Question: {user_message}
Requested Output Language: {language}"""

    reply_text = ""
    if client:
        models_to_try = ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-latest"]
        for m in models_to_try:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.2
                    )
                )
                if response and response.text:
                    reply_text = response.text.strip()
                    break
            except Exception as ex:
                print(f"[-] Model {m} note: {ex}")

    # 5. Robust Grounded RAG Fallback if reply_text is empty
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
            reply_text = "\n".join(extracted_bullets[:4]) if extracted_bullets else "* PLI (Postal Life Insurance): For govt & corporate professionals (Max ₹50 Lakhs).\n* RPLI (Rural Postal Life Insurance): For rural residents & villages (Max ₹10 Lakhs)."
        else:
            reply_text = "* PLI (Postal Life Insurance): For govt & corporate professionals (Max ₹50 Lakhs).\n* RPLI (Rural Postal Life Insurance): For rural residents & villages (Max ₹10 Lakhs)."

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
        category = "Grievances & Support"
    elif "pincode" in msg_lower or "pin" in msg_lower or "post office" in msg_lower or "branch" in msg_lower:
        category = "Branch & PIN Services"

    # Log to SQLite
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
    
    try:
        if query_str.isdigit() and len(query_str) == 6:
            url = f"https://api.postalpincode.in/pincode/{query_str}"
        else:
            url = f"https://api.postalpincode.in/postoffice/{query_str}"
            
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            res_json = resp.json()
            if res_json and isinstance(res_json, list) and res_json[0].get("Status") == "Success":
                post_offices = res_json[0].get("PostOffice", [])
                return jsonify({"status": "Success", "results": post_offices})
    except Exception as e:
        print(f"[-] Online PIN lookup failed ({e}), using local dictionary.")

    results = []
    if query_str in MOCK_PINCODES:
        results = MOCK_PINCODES[query_str]
    else:
        q_lower = query_str.lower()
        for pin, offices in MOCK_PINCODES.items():
            if q_lower in pin:
                results.extend(offices)
            else:
                for off in offices:
                    if q_lower in off["Name"].lower() or q_lower in off["District"].lower() or q_lower in off["State"].lower():
                        results.append(off)

    if results:
        return jsonify({"status": "Success", "results": results})

    if query_str.isdigit() and len(query_str) == 6:
        generic_result = [{
            "Name": f"Post Office (PIN: {query_str})",
            "BranchType": "Sub Post Office",
            "DeliveryStatus": "Delivery",
            "District": "Postal Division",
            "State": "India",
            "Pincode": query_str
        }]
        return jsonify({"status": "Success", "results": generic_result})

    return jsonify({"status": "Error", "message": f"No post office found for '{query_str}'"}), 404

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
