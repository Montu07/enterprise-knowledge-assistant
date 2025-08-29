# app/fusion.py
from typing import List, Dict

def fuse_answer(query: str, rag: Dict, sql: Dict) -> Dict:
    """Merge RAG + SQL into a single response with dual citations."""
    # RAG parts
    rag_answer = rag.get("answer", "").strip()
    rag_sources = rag.get("sources", [])

    # SQL parts
    sql_text = sql.get("sql", "")
    sql_rows = sql.get("rows", [])

    # Build a concise fused message
    lines = []
    if rag_answer:
        lines.append("**Summary (from documents):**")
        lines.append(rag_answer)

    if sql_rows:
        lines.append("\n**Key Figures (from SQL):**")
        # show up to 5 rows
        head = sql_rows[:5]
        # format table-ish text
        if head and isinstance(head[0], dict):
            cols = list(head[0].keys())
            header = " | ".join(cols)
            sep = " | ".join(["---"] * len(cols))
            lines.append(header)
            lines.append(sep)
            for r in head:
                lines.append(" | ".join(str(r[c]) for c in cols))
        else:
            lines.append(str(head))

    if rag_sources:
        lines.append("\n**Sources:**")
        for i, s in enumerate(rag_sources, 1):
            src = s.get("source", "doc")
            page = s.get("page")
            tag = f"{src}" if page is None else f"{src}#p{page}"
            lines.append(f"[{i}] {tag}")

    if sql_text:
        lines.append("\n**SQL Used:**")
        lines.append(f"```sql\n{sql_text}\n```")

    return {"mode": "hybrid", "answer": "\n".join(lines), "rows": sql_rows, "sql": sql_text, "sources": rag_sources}
