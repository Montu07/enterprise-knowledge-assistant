# etl/ingest_pdfs.py
from pathlib import Path
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from app.config import OPENAI_API_KEY, EMBEDDING_MODEL

DOCS_DIR = Path("data/docs")
INDEX_DIR = Path("index/faiss")

def load_docs() -> List:
    if not DOCS_DIR.exists():
        raise FileNotFoundError("Create folder data/docs and add at least one PDF.")
    docs = []
    for pdf in DOCS_DIR.glob("*.pdf"):
        loader = PyPDFLoader(str(pdf))
        pages = loader.load()
        # keep file name/page for citations later
        for p in pages:
            p.metadata["source"] = pdf.name
        docs.extend(pages)
    if not docs:
        raise ValueError("No PDFs found in data/docs. Add some and retry.")
    return docs

def chunk_docs(docs: List):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_documents(docs)

def build_faiss_index():
    print("📥 Loading PDFs...")
    docs = load_docs()
    print(f"→ Loaded {len(docs)} pages")

    print("✂️  Chunking...")
    chunks = chunk_docs(docs)
    print(f"→ Created {len(chunks)} chunks")

    # Prepare texts + metadatas
    texts = [c.page_content for c in chunks]
    metas = [c.metadata for c in chunks]

    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS
    import time

    # Use smaller model if you hit rate limits (set in .env)
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)

    print("🧠 Embedding & indexing in batches (to respect rate limits)...")
    BATCH = 64  # safe batch size; decrease if you still get 429
    vs = None

    for i in range(0, len(texts), BATCH):
        t_batch = texts[i:i+BATCH]
        m_batch = metas[i:i+BATCH]

        # First batch: create the index; subsequent: add to it
        if vs is None:
            vs = FAISS.from_texts(t_batch, embeddings, metadatas=m_batch)
        else:
            vs.add_texts(t_batch, metadatas=m_batch)

        # Tiny delay to avoid TPM spikes
        time.sleep(1.5)

        print(f"   → Embedded {i + len(t_batch)}/{len(texts)}")

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vs.save_local(str(INDEX_DIR))
    print(f"✅ Saved FAISS index to: {INDEX_DIR.resolve()}")

if __name__ == "__main__":
    build_faiss_index()
