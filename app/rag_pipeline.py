# app/rag_pipeline.py
from typing import List, Tuple
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import HumanMessage, SystemMessage
from app.config import OPENAI_API_KEY, CHAT_MODEL, EMBEDDING_MODEL

INDEX_PATH = "index/faiss"

def _load_vectorstore():
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)
    # required by FAISS loader on disk
    return FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)

def retrieve(query: str, k: int = 5) -> List[dict]:
    vs = _load_vectorstore()
    docs = vs.similarity_search(query, k=k)
    return [{"text": d.page_content, "source": d.metadata.get("source"), "page": d.metadata.get("page")} for d in docs]

def generate_answer(query: str, ctx: List[dict]) -> Tuple[str, List[dict]]:
    # Build a context block with numbered sources
    ctx_str = ""
    for i, c in enumerate(ctx, 1):
        src = c["source"]
        page = c["page"]
        tag = f"{src}" if page is None else f"{src}#p{page}"
        ctx_str += f"[{i}] ({tag})\n{c['text']}\n\n"

    system = (
        "You answer strictly using the provided context. "
        "When you state a fact, append a citation like [1], [2]. "
        "If the answer is not in the context, say you cannot find it."
    )
    user = f"Context:\n{ctx_str}\nQuestion: {query}\nReturn a concise answer with inline [n] citations."

    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0, api_key=OPENAI_API_KEY)
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    return resp.content, ctx

def ask(query: str, k: int = 5):
    ctx = retrieve(query, k=k)
    answer, sources = generate_answer(query, ctx)
    return {"answer": answer, "sources": sources}
