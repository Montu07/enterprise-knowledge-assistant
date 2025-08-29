import os
import io
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Enterprise Knowledge Assistant", page_icon="🤖", layout="centered")
st.title("Enterprise Knowledge Assistant")

default_api = os.getenv("API_URL", "http://127.0.0.1:8000/ask")
api_url = st.text_input("API URL", default_api)

col1, col2 = st.columns(2)
with col1:
    mode = st.selectbox("Mode", ["auto", "rag", "sql", "hybrid"])
with col2:
    k = st.number_input("RAG top-K", min_value=1, max_value=15, value=5, step=1)

q = st.text_area("Ask a question about your PDFs or data", height=90)
api_key = st.text_input("Optional API Key (x-api-key header)", type="password")

if st.button("Ask") and q.strip():
    try:
        headers = {}
        if api_key:
            headers["x-api-key"] = api_key
        r = requests.get(api_url, params={"q": q, "mode": mode, "k": k}, headers=headers, timeout=60)
        if r.ok:
            data = r.json()
            st.caption(f"Resolved mode: **{data.get('mode', mode)}**")
            if "route_reason" in data:
                rr = data["route_reason"]
                st.caption(f"Router hints → metrics: {rr.get('matched_metrics')}, doc: {rr.get('matched_doc_words')}")
            if "answer" in data:
                st.markdown("### Answer")
                st.markdown(data["answer"])

            rows = data.get("rows", [])
            if rows:
                st.markdown("### SQL Rows")
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)

                # CSV download
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download rows as CSV",
                    data=csv_bytes,
                    file_name="results.csv",
                    mime="text/csv",
                )

            if "sql" in data and data["sql"]:
                with st.expander("SQL Used"):
                    st.code(data["sql"], language="sql")
        else:
            st.error(f"{r.status_code} {r.text}")
    except Exception as e:
        st.error(str(e))
