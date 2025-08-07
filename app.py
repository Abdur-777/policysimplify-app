import streamlit as st
import PyPDF2
import openai
import os
import pandas as pd
import json
from dotenv import load_dotenv
from datetime import datetime
from fpdf import FPDF
from google.cloud import storage
from models import create_db, SessionLocal, PolicyDoc, AuditLog

# === CONFIG ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET")
GCS_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

client = openai.OpenAI(api_key=OPENAI_API_KEY)
storage_client = storage.Client.from_service_account_json(GCS_KEY_PATH)
bucket = storage_client.bucket(GCS_BUCKET)

COUNCIL_NAME = "Wyndham City Council"
COUNCIL_LOGO = "https://www.wyndham.vic.gov.au/themes/custom/wyndham/logo.png"
GOV_ICON = "https://cdn-icons-png.flaticon.com/512/3209/3209872.png"

st.set_page_config(page_title="PolicySimplify AI", page_icon="✅", layout="centered")
st.markdown("""
    <style>
    body, .stApp { background-color: #eaf3fa; }
    .main { background-color: #eaf3fa; }
    .reportview-container { background-color: #eaf3fa; }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background:#1764a7;padding:20px 0 10px 0;border-radius:16px 16px 0 0;">
    <div style="display:flex;flex-direction:column;align-items:center;gap:0;">
        <img src="{GOV_ICON}" width="40" style="margin-bottom:8px" />
        <div style="font-size:2.1em;font-weight:700;color:white;">PolicySimplify AI</div>
        <span style="color:#bfe2ff;font-size:1.08em;">Council: <b>{COUNCIL_NAME}</b></span>
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown("""
<div style="margin-top:12px; margin-bottom:12px;">
    <div style="text-align:center;font-size:1.13em;color:#1764a7;">
        Upload council policies & instantly see what matters.<br>
        <span style="color:#59c12a;font-weight:500;">Australian-hosted • Secure • Unlimited uploads</span>
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# === DB SETUP ===
create_db()
db = SessionLocal()

def save_pdf_to_gcs(pdf_file, filename):
    blob = bucket.blob(filename)
    pdf_file.seek(0)
    blob.upload_from_file(pdf_file, content_type="application/pdf")
    blob.make_public()
    return blob.public_url

def extract_pdf_text(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() or ""
    return text

def ai_summarize(text):
    prompt = f"""
You are a compliance AI assistant for Australian councils.
Given the following policy document, provide:

1. A plain-English summary (3-5 sentences).
2. A bullet-point list of every compliance obligation, including:
   - What must be done
   - Deadline (if any)
   - Who is responsible (if possible)
Format your response as:
Summary:
...
Obligations:
- Obligation (deadline, responsible)
- ...
Policy text:
\"\"\"
{text[:5000]}
\"\"\"
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=700
    )
    return response.choices[0].message.content.strip()

def ai_chat(query, all_policy_text):
    prompt = f"""
You are a helpful AI compliance assistant. Here is the combined text of all policies uploaded:

\"\"\"{all_policy_text[:6000]}\"\"\"

Answer this council staff question using ONLY the info above. If unsure, say "Not specified in current policies."

Question: {query}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400
    )
    return response.choices[0].message.content.strip()

uploaded_files = st.file_uploader("📄 Upload Policy PDF(s)", type=["pdf"], accept_multiple_files=True)
if uploaded_files:
    for uploaded_file in uploaded_files:
        # Only upload if not already in DB
        exists = db.query(PolicyDoc).filter_by(filename=uploaded_file.name).first()
        if not exists:
            with st.spinner(f"Uploading {uploaded_file.name} to GCS..."):
                gcs_url = save_pdf_to_gcs(uploaded_file, uploaded_file.name)
                pdf_text = extract_pdf_text(uploaded_file)
                ai_response = ai_summarize(pdf_text)
                summary_part, obligations_part = ai_response.split("Obligations:", 1) if "Obligations:" in ai_response else (ai_response, "")
                obligations_list = []
                for line in obligations_part.strip().split("\n"):
                    if line.strip().startswith("-"):
                        obligations_list.append(line.strip()[1:].strip())
                doc = PolicyDoc(
                    filename=uploaded_file.name,
                    gcs_url=gcs_url,
                    summary=summary_part.strip(),
                    obligations=json.dumps(obligations_list),
                    upload_time=datetime.utcnow()
                )
                db.add(doc)
                db.commit()
                db.refresh(doc)
                audit = AuditLog(
                    action="upload",
                    filename=uploaded_file.name,
                    obligation="",
                    who="You",
                    time=datetime.utcnow()
                )
                db.add(audit)
                db.commit()
    st.success("PDF(s) uploaded and processed!")

# === Recent Uploads Section ===
st.markdown("## 📂 Recent Uploads")
recent_docs = db.query(PolicyDoc).order_by(PolicyDoc.upload_time.desc()).limit(7).all()
if recent_docs:
    for doc in recent_docs:
        with st.expander(f"📑 {doc.filename} — [Download PDF]({doc.gcs_url})", expanded=False):
            st.markdown(f"**Summary:**<br>{doc.summary}", unsafe_allow_html=True)
            st.markdown("**Obligations & Actions:**")
            obligations_list = json.loads(doc.obligations)
            for obl in obligations_list:
                st.markdown(f"- ⬜️ {obl}")
            st.caption("AI-generated. Please review obligations before action.")
            st.markdown(f'<a href="{doc.gcs_url}" download target="_blank">⬇️ Download Original PDF</a>', unsafe_allow_html=True)
else:
    st.info("No uploads yet. Upload a PDF to get started.")

# === Full-text Search Section ===
st.markdown("---")
st.markdown("## 🔍 Full-Text Search")
search_text = st.text_input("Search summaries or obligations...", key="search")
search_results = []
if search_text:
    docs = db.query(PolicyDoc).all()
    for doc in docs:
        obligations_list = json.loads(doc.obligations)
        for obl in obligations_list:
            if (search_text.lower() in obl.lower() or search_text.lower() in doc.summary.lower()):
                search_results.append({
                    "Filename": doc.filename,
                    "Obligation": obl,
                    "Summary": doc.summary[:100] + "..." if len(doc.summary) > 100 else doc.summary,
                    "Upload Time": doc.upload_time.strftime("%Y-%m-%d %H:%M"),
                    "Download": doc.gcs_url
                })
if search_results:
    df = pd.DataFrame(search_results)
    st.dataframe(df, use_container_width=True)
    st.download_button(
        label="Download Search Results CSV",
        data=df.to_csv(index=False),
        file_name="search_results.csv",
        mime="text/csv"
    )

# === Policy Q&A Chatbot ===
st.markdown("---")
st.markdown("## 🤖 Ask Your Policies (AI Chat)")
st.caption("Type a question about your policies. The AI answers ONLY using your uploaded documents.")
all_policy_text = "\n".join([extract_pdf_text(open(bucket.blob(doc.filename).download_as_bytes(), "rb")) for doc in recent_docs])
query = st.text_input("Ask a policy/compliance question", key="policy_qa")
if query:
    with st.spinner("Getting answer..."):
        answer = ai_chat(query, all_policy_text)
    st.success(answer)

# === Audit Log Section ===
st.markdown("---")
st.markdown("## 🕵️ Audit Log & Download")
audit_logs = db.query(AuditLog).order_by(AuditLog.time.desc()).limit(100).all()
if audit_logs:
    audit_data = [{
        "Action": log.action,
        "Filename": log.filename,
        "Obligation": log.obligation,
        "Who": log.who,
        "Time": log.time.strftime("%Y-%m-%d %H:%M")
    } for log in audit_logs]
    audit_df = pd.DataFrame(audit_data)
    st.dataframe(audit_df, use_container_width=True)
    st.download_button(
        label="Download Audit Log CSV",
        data=audit_df.to_csv(index=False),
        file_name="audit_log.csv",
        mime="text/csv"
    )

st.markdown("---")
st.markdown("""
<span style='color: #59c12a; font-weight:bold;'>PolicySimplify AI – Built for Australian councils. All data hosted securely in Australia (GCS).</span>
""", unsafe_allow_html=True)
