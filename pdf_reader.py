import os
import glob
import pypdf

def chunk_text(text, source_name, page_num=1, chunk_size=250, overlap=50):
    """
    Chunks text into overlapping semantic segments (~250 words each) with source metadata.
    """
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
        if len(chunk_str) > 30:  # Ignore trivial noise chunks
            source_display = f"{source_name} (Page {page_num})" if page_num > 0 else source_name
            chunks.append({
                "text": chunk_str,
                "source": source_name,
                "page": page_num,
                "chunk_id": chunk_id,
                "source_display": source_display
            })
            chunk_id += 1
    return chunks

def load_dynamic_knowledge_base(docs_dir=None):
    """
    Dynamically scans all .pdf and .txt files in data/docs/ and returns list of chunk dicts.
    """
    if docs_dir is None:
        docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "docs")
        
    if not os.path.exists(docs_dir):
        print(f"[!] Warning: Directory '{docs_dir}' does not exist.")
        return []
        
    knowledge_base = []
    
    # Process PDF files
    pdf_files = glob.glob(os.path.join(docs_dir, "*.pdf"))
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        try:
            reader = pypdf.PdfReader(pdf_path)
            total_pages = len(reader.pages)
            extracted_chunks = 0
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    page_chunks = chunk_text(page_text, filename, page_num=idx + 1)
                    knowledge_base.extend(page_chunks)
                    extracted_chunks += len(page_chunks)
            print(f"    [+] PDF '{filename}': {total_pages} pages -> {extracted_chunks} chunks.")
        except Exception as e:
            print(f"    [-] Error reading PDF '{filename}': {e}")
            
    # Process TXT files
    txt_files = glob.glob(os.path.join(docs_dir, "*.txt"))
    for txt_path in txt_files:
        filename = os.path.basename(txt_path)
        try:
            with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if content.strip():
                txt_chunks = chunk_text(content, filename, page_num=0)
                knowledge_base.extend(txt_chunks)
                print(f"    [+] TXT '{filename}': {len(txt_chunks)} chunks.")
        except Exception as e:
            print(f"    [-] Error reading TXT '{filename}': {e}")
            
    print(f"[*] Dynamic Knowledge Extractor complete: Total {len(knowledge_base)} chunks loaded.")
    return knowledge_base

if __name__ == "__main__":
    kb = load_dynamic_knowledge_base()
    print(f"Indexed {len(kb)} chunks total.")
