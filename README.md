# Dak Sahayak (डाक सहायक) - Official India Post AI Assistant

Dak Sahayak is a decoupled, full-stack AI assistant for India Post built with **Next.js**, **Flask**, **Google Gemini 3.6 Flash**, and **Supabase (Auth + Vector Database + Chat Persistence)**.

---

## System Architecture

```
dak-sahayak-ai/
├── dak-backend/              # Flask REST API (Port 5000)
│   ├── app.py                # Core routes, streaming responses, CORS
│   ├── supabase_client.py    # Supabase authentication & database helpers
│   ├── vector_search.py      # Gemini text embeddings & Supabase pgvector RAG
│   ├── calculator.py         # Speed Post tariffs & financial scheme formulas
│   ├── schema.sql            # Supabase database schema & RPC definitions
│   ├── ingest_supabase.py    # Vector knowledge base embedding ingestion script
│   ├── ingest_pincodes.py    # PIN code directory CSV ingestion script
│   ├── data/                 # Source knowledge files (.txt, .json, .csv)
│   └── requirements.txt
│
├── dak-frontend/             # Next.js 14 Web Application (Port 3000)
│   ├── src/
│   │   ├── app/              # App router (login, signup, chat workspace)
│   │   ├── components/       # UI Components (Sidebar, ChatArea, Input, Modals)
│   │   ├── lib/              # Supabase browser client & backend API client
│   │   └── styles/           # Global theme & Gemini-like styling
│   └── package.json
│
├── .gitignore
└── README.md
```

---

## Features

1. **Supabase Authentication**: Secure user sign up, sign in, and session management with Row Level Security (RLS).
2. **Supabase Vector Database (pgvector)**: 768-dimensional dense vector embeddings generated via Gemini for semantic document search.
3. **Persistent Chat Sessions**: Gemini-style sidebar with conversation list, message history, and persistence across refreshes.
4. **Token-by-Token Streaming**: Live word-by-word streaming responses powered by Gemini 3.6 Flash.
5. **Interactive Tools & Modals**:
   - **Domestic Speed Post Tariff Calculator**: Weight & distance slab breakdown with 18% GST.
   - **India Post PIN Directory Search**: Look up Post Offices by 6-digit PIN or locality.
   - **Geolocation (My PIN)**: Automatic PIN detection based on browser GPS.
   - **POSB Small Savings ROI Calculator**: Maturity and pension payout calculations for SSA, PPF, SCSS, MIS, NSC, and KVP.
6. **Multi-Language Support**: English, Hindi, Kannada, Tamil, Telugu, Marathi, and Bengali.

---

## Getting Started

### 1. Backend Setup
```bash
cd dak-backend
pip install -r requirements.txt
python app.py
```
Backend runs on `http://localhost:5000`.

### 2. Frontend Setup
```bash
cd dak-frontend
npm install
npm run dev
```
Frontend runs on `http://localhost:3000`.
