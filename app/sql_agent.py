# app/sql_agent.py
import re
import sqlite3
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from app.config import OPENAI_API_KEY, CHAT_MODEL

DB_PATH = "db/retail.db"

# ✅ Guardrail: allow ONLY SELECT queries (block INSERT/UPDATE/DELETE/DROP, etc.)
READ_ONLY = re.compile(r"^\s*SELECT\b", re.IGNORECASE | re.DOTALL)

# Minimal schema context so the model generates valid SQL
SCHEMA = """
You can query a SQLite database with schema:

TABLE customers(customer_id INTEGER PRIMARY KEY, segment TEXT, region TEXT)
TABLE products(product_id INTEGER PRIMARY KEY, category TEXT, price REAL)
TABLE sales(sale_id INTEGER PRIMARY KEY, customer_id INTEGER, product_id INTEGER, sale_date TEXT, qty INTEGER, revenue REAL)

Joins:
sales.customer_id -> customers.customer_id
sales.product_id  -> products.product_id
"""

SYSTEM = (
    "You are a SQL assistant. Generate a SINGLE safe SELECT query for SQLite based on the user's question. "
    "Rules: only SELECT; include LIMIT 100; prefer ISO dates (YYYY-MM-DD); use correct table/column names. "
    "Return ONLY the SQL, no commentary."
)

def _sanitize_llm_sql(raw: str) -> str:
    """Normalize LLM output to a clean single SELECT statement."""
    raw = raw.strip()

    # Remove fenced code blocks like ```sql ... ``` or ``` ... ```
    raw = re.sub(r"^```(?:sql)?\s*|\s*```$", "", raw, flags=re.IGNORECASE | re.DOTALL).strip()

    # Remove a lone 'sql' tag on the first line
    raw = re.sub(r"^\s*sql\s*\n", "", raw, flags=re.IGNORECASE)

    # Keep from the first SELECT onward (drop any prose before it)
    m = re.search(r"SELECT\b.*", raw, flags=re.IGNORECASE | re.DOTALL)
    sql = m.group(0).strip() if m else raw

    # Drop trailing semicolon and excess whitespace
    sql = sql.rstrip(";").strip()
    return sql

def generate_sql(question: str) -> str:
    """Generate a safe, read-only SQL query for SQLite from a natural-language question."""
    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0, api_key=OPENAI_API_KEY)
    prompt = f"{SYSTEM}\n\n{SCHEMA}\n\nQuestion: {question}\nSQL:"
    raw = llm.invoke(prompt).content
    sql = _sanitize_llm_sql(raw)

    # Guardrails
    if not READ_ONLY.match(sql):
        raise ValueError(f"Unsafe or non-SELECT SQL blocked:\n{sql}")
    if "limit" not in sql.lower():
        sql += " LIMIT 100"
    return sql

def run_sql(sql: str) -> Dict[str, Any]:
    """Execute SQL against the local SQLite DB and return rows as dicts."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(sql)
    rows = cur.fetchall()
    con.close()
    return {"sql": sql, "rows": [dict(r) for r in rows]}

if __name__ == "__main__":
    # Simple manual test
    q = "total revenue by category"
    sql = generate_sql(q)
    print("SQL =>", sql)
    print(run_sql(sql))
