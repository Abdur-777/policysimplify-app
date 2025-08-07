import streamlit as st
import PyPDF2
import openai
import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
from google.cloud import storage

# === CONFIG ===
COUNCIL_NAME = "Wyndham City Council"
COUNCIL_LOGO = "https://www.wyndham.vic.gov.au/themes/custom/wyndham/logo.png"
GOV_ICON = "https://cdn-icons-png.flaticon.com/512/3209/3209872.png"
UPLOAD_PREFIX = "wyndham/"   # GCS folder prefix, change per council if needed

st.set_page_config(page_title="PolicySimplify AI", page_icon="✅", layout="centered")

st.markdown("""
    <style>
    body, .stApp { background-color: #eaf3fa; }
    .main { background-color: #eaf3fa; }
    .reportview-container { background-color: #eaf3fa; }
    .reminder { color: #fff; background:#e65c5c; padding: 6px 12px; border-radius: 6px; margin-right: 8px; }
    .reminder-upcoming { color: #fff; background:#f3c852; padding: 6px 12px; border-radius: 6px; margin-right: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
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

# === ENV ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GCS_BUCKET = os.getenv("GCS_BUCKET")
client = openai.OpenAI(api_key=OPENAI_API_KEY)
gcs_client = storage.Client()  # Uses GCP IAM if deployed in GCP, else env/service key

# === SESSION STATE ===
if 'obligations' not in st.session_state:
    st.session_state['obligations'] = {}  # key: gcs_key, value: dict

if 'audit_log' not in st.session_state:
    st.session_state['audit_log'] = []

if 'recent_uploads' not in st.session_state:
    st.session_state['recent_uploads'] = []  # last 10 GCS keys

# === GCS UTILS ===
def upload_to_gcs(file, gcs_key):
    bucket = gcs_client.bucket(GCS_BUCKET)
    blob = bucket.blob(gcs_key)
    blob.upload_from_file(file, rewind=True)
    return gcs_key

def get_signed_gcs_url(blob_name, expiration_minutes=10):
    bucket = gcs_client.bucket(GCS_BUCKET)
    blob = bucket.blob(blob_name)
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="GET"
    )
    return url

def list_recent_uploads(prefix=UPLOAD_PREFIX, max_results=10):
    bucket = gcs_client.bucket(GCS_BUCKET)
    blobs = list(bucket.list_blobs(prefix=prefix))
    blobs = sorted(blobs, key=lambda b: b.updated, reverse=True)
    return blobs[:max_results]

# === PDF TEXT & AI ===
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

# === FILE UPLOAD ===
uploaded_files = st.file_uploader("📄 Upload Policy PDF(s)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    all_policy_text = ""
    dashboard_data = []
    for uploaded_file in uploaded_files:
        pdf_text = extract_pdf_text(uploaded_file)
        all_policy_text += "\n\n" + pdf_text

        # --- GCS Save & Log ---
        gcs_key = UPLOAD_PREFIX + uploaded_file.name
        if gcs_key not in st.session_state['obligations']:
            with st.spinner(f"Uploading {uploaded_file.name} to secure council storage..."):
                uploaded_file.seek(0)
                upload_to_gcs(uploaded_file, gcs_key)
            with st.spinner(f"Processing {uploaded_file.name} with AI..."):
                ai_response = ai_summarize(pdf_text)
                summary_part, obligations_part = ai_response.split("Obligations:", 1) if "Obligations:" in ai_response else (ai_response, "")
                obligations_list = []
                for line in obligations_part.strip().split("\n"):
                    if line.strip().startswith("-"):
                        obligations_list.append({
                            "text": line.strip()[1:].strip(),
                            "done": False,
                            "assigned_to": "",
                            "deadline": "",
                            "timestamp": None
                        })
                st.session_state['obligations'][gcs_key] = {
                    "summary": summary_part.strip(),
                    "obligations": obligations_list,
                    "filename": uploaded_file.name
                }
                st.session_state['audit_log'].append({
                    "action": "upload",
                    "file": uploaded_file.name,
                    "obligation": "",
                    "who": "You",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                # Track recent uploads for display
                st.session_state['recent_uploads'].insert(0, gcs_key)
                st.session_state['recent_uploads'] = st.session_state['recent_uploads'][:10]

    # --- REMINDERS ---
    st.markdown("### ⏰ Reminders")
    # For simplicity, demo skips deadline detection, but you can add color/deadline parsing

    # --- RECENT UPLOADS SECTION ---
    st.markdown("---")
    st.markdown("### 📂 Recent Uploads")
    blobs = list_recent_uploads()
    for blob in blobs:
        signed_url = get_signed_gcs_url(blob.name)
        st.markdown(f"**{os.path.basename(blob.name)}** — {blob.updated.strftime('%Y-%m-%d %H:%M')} &nbsp;&nbsp; [🔽 Download]({signed_url})", unsafe_allow_html=True)

    # --- DASHBOARD ---
    st.markdown("---")
    st.markdown("## 📊 Compliance Dashboard & Export")
    for gcs_key, doc in st.session_state['obligations'].items():
        with st.expander(f"📑 {doc['filename']}", expanded=False):
            st.markdown(f"**Summary:**<br>{doc['summary']}", unsafe_allow_html=True)
            st.markdown("**Obligations & Actions:**")
            for idx, obl in enumerate(doc['obligations']):
                cols = st.columns([0.07,0.68,0.13,0.12])
                with cols[0]:
                    checked = st.checkbox("", value=obl['done'], key=f"{gcs_key}_check_{idx}")
                    if checked != obl['done']:
                        doc['obligations'][idx]['done'] = checked
                        doc['obligations'][idx]['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        st.session_state['audit_log'].append({
                            "action": "check" if checked else "uncheck",
                            "file": doc['filename'],
                            "obligation": obl['text'],
                            "who": "You",
                            "time": doc['obligations'][idx]['timestamp']
                        })
                with cols[1]:
                    st.markdown(obl['text'])
                with cols[2]:
                    assigned_to = st.text_input(
                        "Assign", value=obl.get("assigned_to",""), key=f"{gcs_key}_assign_{idx}", label_visibility="collapsed", placeholder="Assign to"
                    )
                    if assigned_to != obl.get("assigned_to",""):
                        doc['obligations'][idx]['assigned_to'] = assigned_to
                        st.session_state['audit_log'].append({
                            "action": "assign",
                            "file": doc['filename'],
                            "obligation": obl['text'],
                            "who": assigned_to,
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                with cols[3]:
                    deadline = st.text_input(
                        "Deadline", value=obl.get("deadline",""), key=f"{gcs_key}_deadline_{idx}", label_visibility="collapsed", placeholder="Deadline (YYYY-MM-DD)"
                    )
                    if deadline != obl.get("deadline",""):
                        doc['obligations'][idx]['deadline'] = deadline
                        st.session_state['audit_log'].append({
                            "action": "deadline_change",
                            "file": doc['filename'],
                            "obligation": obl['text'],
                            "who": "You",
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
            st.caption("AI-generated. Please review obligations before action.")

    # === POLICY Q&A CHAT ===
    st.markdown("---")
    st.markdown("## 🤖 Ask Your Policies (AI Chat)")
    st.caption("Type a question about your policies. The AI answers ONLY using your uploaded documents.")
    query = st.text_input("Ask a policy/compliance question", key="policy_qa")
    if query:
        with st.spinner("Getting answer..."):
            answer = ai_chat(query, all_policy_text)
        st.success(answer)

    # === AUDIT LOG ===
    st.markdown("---")
    st.markdown("## 🕵️ Audit Log")
    st.caption("All major actions are tracked for compliance and audit reporting.")
    audit_df = pd.DataFrame(st.session_state['audit_log'])
    st.dataframe(audit_df, use_container_width=True)
    st.download_button(
        label="Download Audit Log CSV",
        data=audit_df.to_csv(index=False),
        file_name="audit_log.csv",
        mime="text/csv"
    )

else:
    st.info("Upload one or more council policy PDFs to begin.")

st.markdown("---")
st.markdown("""
<span style='color: #59c12a; font-weight:bold;'>PolicySimplify AI – Built for Australian councils. All data hosted securely in Australia.</span>
""", unsafe_allow_html=True)
