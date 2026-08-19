import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from supabase_client import get_supabase_admin

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini_client = None

def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set.")
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client

def embed_text(text: str) -> list[float]:
    """Generates a 768-dimensional embedding vector for input text."""
    client = get_gemini_client()
    try:
        res = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        if hasattr(res, "embedding") and res.embedding:
            return res.embedding.values
        elif hasattr(res, "embeddings") and res.embeddings:
            return res.embeddings[0].values
        return []
    except Exception as e:
        print(f"[-] Error generating embedding: {e}")
        return []

def search_documents(query: str, top_k: int = 3, match_threshold: float = 0.3) -> list[dict]:
    """Embeds the query and performs vector similarity search against Supabase documents table."""
    embedding = embed_text(query)
    if not embedding:
        return []

    try:
        admin = get_supabase_admin()
        res = admin.rpc("match_documents", {
            "query_embedding": embedding,
            "match_threshold": match_threshold,
            "match_count": top_k
        }).execute()

        matches = res.data or []
        formatted = []
        for m in matches:
            meta = m.get("metadata") or {}
            formatted.append({
                "id": m.get("id"),
                "text": m.get("content", ""),
                "similarity": m.get("similarity", 0.0),
                "source": meta.get("source", "Supabase Vector DB"),
                "source_display": meta.get("scheme_name", meta.get("service", meta.get("source", "India Post Official Guide"))),
                "metadata": meta
            })
        return formatted
    except Exception as e:
        print(f"[-] Supabase vector search error: {e}")
        return []
