# app/api.py
import os
from functools import lru_cache
from fastapi import FastAPI, Query, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.rag_pipeline import ask as ask_rag
from app.sql_agent import generate_sql, run_sql
from app.fusion import fuse_answer

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

@app.get("/health")
def health():
    return {"status": "ok"}

def is_metrics_q(q: str) -> bool:
    q = q.lower()
    metrics_words = [
        "sum","total","count","average","avg","trend",
        "by month","by category","by region","top",
        "revenue","price","qty","quantity","segment","group by"
    ]
    return any(w in q for w in metrics_words)

def is_doc_q(q: str) -> bool:
    q = q.lower()
    doc_words = ["policy","manual","10-k","explain","note","according","audit","warranty","define","definition"]
    return any(w in q for w in doc_words)

def route_reason(q: str):
    ql = q.lower()
    metrics_words = [
        "sum","total","count","average","avg","trend",
        "by month","by category","by region","top",
        "revenue","price","qty","quantity","segment","group by"
    ]
    doc_words = ["policy","manual","10-k","explain","note","according","audit","warranty","define","definition"]
    matched_metrics = [w for w in metrics_words if w in ql]
    matched_doc = [w for w in doc_words if w in ql]
    return {"matched_metrics": matched_metrics, "matched_doc_words": matched_doc}

@lru_cache(maxsize=256)
def ask_rag_cached(q: str, k: int):
    # simple cache for repeated doc questions
    return ask_rag(q, k=k)

@lru_cache(maxsize=256)
def run_sql_with_year_fallback_cached(nl_q: str):
    """
    Run SQL; if it filters to current year via strftime('%Y','now') and returns 0 rows,
    retry with last full year (2024 for our seed).
    """
    sql = generate_sql(nl_q)
    result = run_sql(sql)
    if not result["rows"] and "strftime('%Y', 'now')" in sql:
        sql_fallback = sql.replace("strftime('%Y', 'now')", "'2024'")
        result = run_sql(sql_fallback)
        result["sql"] = sql_fallback
    return result

@app.get("/ask")
def ask_get(
    q: str = Query(..., description="Your question"),
    mode: str = Query("auto", description="rag | sql | hybrid | auto"),
    k: int = Query(5, ge=1, le=15, description="Top-K documents for RAG"),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
):
    # Optional API key gate: set APP_API_KEY in environment to enable
    req_key = os.getenv("APP_API_KEY")
    if req_key and x_api_key != req_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    reason = route_reason(q)

    # Force specific modes
    if mode == "rag":
        rag = ask_rag_cached(q, k)
        return {"mode": "rag", "route_reason": reason, **rag}

    if mode == "sql":
        result = run_sql_with_year_fallback_cached(q)
        return {
            "mode": "sql",
            "route_reason": reason,
            "answer": f"SQL result ({len(result['rows'])} rows)",
            "sql": result["sql"],
            "rows": result["rows"],
        }

    if mode == "hybrid":
        rag = ask_rag_cached(q, k)
        sql_res = run_sql_with_year_fallback_cached(q)
        fused = fuse_answer(q, rag, sql_res)
        fused["route_reason"] = reason
        return fused

    # --- auto router ---
    metrics, docy = is_metrics_q(q), is_doc_q(q)
    if metrics and docy:
        rag = ask_rag_cached(q, k)
        sql_res = run_sql_with_year_fallback_cached(q)
        fused = fuse_answer(q, rag, sql_res)
        fused["route_reason"] = reason
        return fused
    if metrics:
        sql_res = run_sql_with_year_fallback_cached(q)
        return {
            "mode": "sql",
            "route_reason": reason,
            "answer": f"SQL result ({len(sql_res['rows'])} rows)",
            "sql": sql_res["sql"],
            "rows": sql_res["rows"],
        }
    rag = ask_rag_cached(q, k)
    return {"mode": "rag", "route_reason": reason, **rag}
