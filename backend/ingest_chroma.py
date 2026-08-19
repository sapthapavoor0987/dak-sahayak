import os
import json
import chromadb

CHROMA_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_data")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def get_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
    collection = client.get_or_create_collection(
        name="postal_knowledge",
        metadata={"hnsw:space": "cosine"}
    )
    return collection

def ingest_postal_knowledge():
    print(f"[*] Initializing persistent ChromaDB at '{CHROMA_DATA_PATH}'...")
    collection = get_chroma_collection()

    documents = []
    metadatas = []
    ids = []

    # 1. Ingest Savings Schemes
    schemes_path = os.path.join(DATA_DIR, "savings_schemes.json")
    if os.path.exists(schemes_path):
        with open(schemes_path, "r", encoding="utf-8") as f:
            schemes = json.load(f)

        for idx, s in enumerate(schemes):
            doc_id = f"scheme_{s.get('scheme_id', idx)}"
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
            metadata = {
                "source": "savings_schemes.json",
                "type": "savings_scheme",
                "scheme_name": str(s.get("scheme_name", "")),
                "category": str(s.get("category", "")),
                "interest_rate": str(s.get("interest_rate", "")),
                "tax_status": str(s.get("tax_status", ""))
            }
            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(doc_id)

    # 2. Ingest Schedule of Fees
    fees_path = os.path.join(DATA_DIR, "schedule_of_fees.json")
    if os.path.exists(fees_path):
        with open(fees_path, "r", encoding="utf-8") as f:
            fees = json.load(f)

        for idx, fee in enumerate(fees):
            doc_id = f"fee_{idx}"
            doc_text = (
                f"India Post POSB Bank Service Charge: {fee.get('service')}\n"
                f"Fee Rate: {fee.get('fee')}\n"
                f"Details & Conditions: {fee.get('details')}"
            )
            metadata = {
                "source": "schedule_of_fees.json",
                "type": "bank_fee",
                "service": str(fee.get("service", "")),
                "fee": str(fee.get("fee", ""))
            }
            documents.append(doc_text)
            metadatas.append(metadata)
            ids.append(doc_id)

    # 3. Add to Chroma Collection
    if documents:
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"[+] Successfully ingested {len(documents)} documents into ChromaDB collection 'postal_knowledge'.")
    else:
        print("[-] No documents found for ChromaDB ingestion.")

if __name__ == "__main__":
    ingest_postal_knowledge()
