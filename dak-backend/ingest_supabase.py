import os
import json
import glob
import time
from dotenv import load_dotenv
from supabase_client import get_supabase_admin
from vector_search import embed_text

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DOCS_DIR = os.path.join(DATA_DIR, "docs")

def chunk_text(text: str, source_name: str, chunk_size: int = 250, overlap: int = 50):
    words = text.split()
    if not words:
        return []
    chunks = []
    chunk_id = 0
    step = chunk_size - overlap
    if step <= 0:
        step = 100

    for i in range(0, len(words), step):
        chunk_words = words[i:i + chunk_size]
        chunk_str = " ".join(chunk_words).strip()
        if len(chunk_str) > 30:
            chunks.append({
                "text": chunk_str,
                "metadata": {
                    "source": source_name,
                    "chunk_id": chunk_id,
                    "type": "guide_document"
                }
            })
            chunk_id += 1
    return chunks

def ingest_all_knowledge():
    print("[*] Starting Supabase Knowledge Ingestion...")
    admin = get_supabase_admin()
    
    # Check/Clear existing documents
    try:
        admin.table("documents").delete().neq("id", 0).execute()
        print("[*] Cleared existing rows in 'documents' table.")
    except Exception as e:
        print(f"[*] Note on clear documents: {e}")

    records = []

    # 1. Ingest TXT guide files from data/docs
    txt_files = glob.glob(os.path.join(DOCS_DIR, "*.txt"))
    for file_path in txt_files:
        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        chunks = chunk_text(content, filename)
        records.extend(chunks)
        print(f"  [+] {filename}: Prepared {len(chunks)} chunks.")

    # 2. Ingest Savings Schemes JSON
    schemes_path = os.path.join(DATA_DIR, "savings_schemes.json")
    if os.path.exists(schemes_path):
        with open(schemes_path, "r", encoding="utf-8") as f:
            schemes = json.load(f)
        for s in schemes:
            doc_text = (
                f"India Post Small Savings Scheme: {s.get('scheme_name')}\n"
                f"Category: {s.get('category')}\n"
                f"Interest Rate: {s.get('interest_rate')} ({s.get('interest_frequency')})\n"
                f"Minimum Deposit: {s.get('min_deposit')}\n"
                f"Maximum Deposit Limit: {s.get('max_deposit')}\n"
                f"Tenure: {s.get('tenure')}\n"
                f"Eligibility: {s.get('eligibility')}\n"
                f"Tax Benefits & Status: {s.get('tax_status')}\n"
                f"Required KYC Documents: {', '.join(s.get('required_documents', []))}\n"
                f"Rules: {s.get('key_rules')}"
            )
            records.append({
                "text": doc_text,
                "metadata": {
                    "source": "savings_schemes.json",
                    "type": "savings_scheme",
                    "scheme_name": s.get("scheme_name", ""),
                    "category": s.get("category", "")
                }
            })
        print(f"  [+] savings_schemes.json: Prepared {len(schemes)} schemes.")

    # 3. Ingest Schedule of Fees JSON
    fees_path = os.path.join(DATA_DIR, "schedule_of_fees.json")
    if os.path.exists(fees_path):
        with open(fees_path, "r", encoding="utf-8") as f:
            fees = json.load(f)
        for fee in fees:
            doc_text = (
                f"India Post POSB Bank Service Charge: {fee.get('service')}\n"
                f"Fee Rate: {fee.get('fee')}\n"
                f"Details & Conditions: {fee.get('details')}"
            )
            records.append({
                "text": doc_text,
                "metadata": {
                    "source": "schedule_of_fees.json",
                    "type": "bank_fee",
                    "service": fee.get("service", ""),
                    "fee": fee.get("fee", "")
                }
            })
        print(f"  [+] schedule_of_fees.json: Prepared {len(fees)} fee records.")

    print(f"\n[*] Total items to embed and insert: {len(records)}")

    # 4. Generate embeddings and insert into Supabase
    success_count = 0
    for idx, item in enumerate(records, 1):
        text = item["text"]
        meta = item["metadata"]
        embedding = embed_text(text)
        if embedding and len(embedding) == 768:
            try:
                admin.table("documents").insert({
                    "content": text,
                    "embedding": embedding,
                    "metadata": meta
                }).execute()
                success_count += 1
                print(f"  [{idx}/{len(records)}] Ingested '{meta.get('source')}' - {meta.get('scheme_name', meta.get('service', 'Chunk'))}")
            except Exception as e:
                print(f"  [-] Error inserting record {idx}: {e}")
        else:
            print(f"  [-] Failed to generate 768-dim embedding for record {idx}")
        time.sleep(0.1)

    print(f"\n[+] Ingestion Complete: {success_count}/{len(records)} documents stored in Supabase Vector DB.")

if __name__ == "__main__":
    ingest_all_knowledge()
