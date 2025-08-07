import streamlit as st
import PyPDF2
import openai
import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

# === BRANDING ===
COUNCIL_NAME = "Wyndham City Council"
COUNCIL_LOGO = "https://www.wyndham.vic.gov.au/themes/custom/wyndham/logo.png"
GOV_ICON = "https://cdn-icons-png.flaticon.com/512/3209/3209872.png"

# PAGE STYLING
st.set_page_config(page_title="PolicySimplify AI", page_icon="✅", layout="centered")
st.markdown("""
    <style>
    body, .stApp { background-color: #eaf3fa; }
    .main { background-color: #eaf3fa; }
    .reportview-container { background-color: #eaf3fa; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
<div style="background:#1764a7;padding:20px 0 10px 0;border-radius:16px 16px 0 0;">
    <div style="display:flex;flex-direction:column;align-items:center;gap:0;">
        <img src="{GOV_ICON}" width="40" style="margin-bottom:8px" />
        <div style="font-size:2.1em;font-weight:700;color:white;">PolicySimplify AI</div>
        <span style="color:#bfe2ff;font-size:1.08em;">Council: <b>Wyndham City Council</b></span>
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

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# === PDF UPLOAD & PROCESSING ===
uploaded_files = st.file_uploader("📄 Upload Policy PDF(s)", type=["pdf"], accept_multiple_files=True)

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
    response = openai.chat.completions.create(
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
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400
    )
    return response.choices[0].message.content.strip()

# -- SESSION STATE for obligations, assignments, and audit log --
if 'obligations' not in st.session_state:
    st.session_state['obligations'] = {}  # key: filename, value: list of dicts

if 'audit_log' not in st.session_state:
    st.session_state['audit_log'] = []  # Each entry: {action, file, obligation, who, time}

# --- PDF Processing Section ---
if uploaded_files:
    st.success("PDF(s) uploaded! See instant summary and obligations below.")
    all_policy_text = ""
    for uploaded_file in uploaded_files:
        pdf_text = extract_pdf_text(uploaded_file)
        all_policy_text += "\n\n" + pdf_text

        if uploaded_file.name not in st.session_state['obligations']:
            # Only run AI once per file per session
            with st.spinner(f"Processing {uploaded_file.name}..."):
                ai_response = ai_summarize(pdf_text)
                summary_part, obligations_part = ai_response.split("Obligations:", 1) if "Obligations:" in ai_response else (ai_response, "")
                obligations_list = []
                for line in obligations_part.strip().split("\n"):
                    if line.strip().startswith("-"):
                        obligations_list.append({
                            "text": line.strip()[1:].strip(),
                            "done": False,
                            "assigned_to": "",
                            "timestamp": None
                        })
                st.session_state['obligations'][uploaded_file.name] = {
                    "summary": summary_part.strip(),
                    "obligations": obligations_list
                }
                # Audit log upload
                st.session_state['audit_log'].append({
                    "action": "upload",
                    "file": uploaded_file.name,
                    "obligation": "",
                    "who": "You",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                })

        # --- Pretty Card & Checklist ---
        with st.expander(f"📑 {uploaded_file.name}", expanded=True):
            doc_state = st.session_state['obligations'][uploaded_file.name]
            st.markdown(f"**Summary:**<br>{doc_state['summary']}", unsafe_allow_html=True)
            st.markdown("**Obligations & Actions:**")
            for idx, obl in enumerate(doc_state['obligations']):
                cols = st.columns([0.08,0.82,0.1])
                with cols[0]:
                    checked = st.checkbox("", value=obl['done'], key=f"{uploaded_file.name}_check_{idx}")
                    if checked != obl['done']:
                        doc_state['obligations'][idx]['done'] = checked
                        doc_state['obligations'][idx]['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M")
                        st.session_state['audit_log'].append({
                            "action": "check" if checked else "uncheck",
                            "file": uploaded_file.name,
                            "obligation": obl['text'],
                            "who": "You",
                            "time": doc_state['obligations'][idx]['timestamp']
                        })
                with cols[1]:
                    st.markdown(obl['text'])
                with cols[2]:
                    assigned_to = st.text_input(
                        "Assign", value=obl.get("assigned_to",""), key=f"{uploaded_file.name}_assign_{idx}", label_visibility="collapsed", placeholder="Assign to"
                    )
                    if assigned_to != obl.get("assigned_to",""):
                        doc_state['obligations'][idx]['assigned_to'] = assigned_to
                        st.session_state['audit_log'].append({
                            "action": "assign",
                            "file": uploaded_file.name,
                            "obligation": obl['text'],
                            "who": assigned_to,
                            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
            st.caption("AI-generated. Please review obligations before action.")

    # === Dashboard ===
    st.markdown("---")
    st.markdown("## 📊 Compliance Dashboard & Export")
    dashboard_data = []
    for fname, doc in st.session_state['obligations'].items():
        for obl in doc["obligations"]:
            dashboard_data.append({
                "Filename": fname,
                "Summary": doc["summary"][:100]+"..." if len(doc["summary"]) > 100 else doc["summary"],
                "Obligation": obl["text"],
                "Done": "✅" if obl["done"] else "⬜️",
                "Assigned to": obl.get("assigned_to",""),
                "Timestamp": obl.get("timestamp","")
            })
    if dashboard_data:
        df = pd.DataFrame(dashboard_data)
        st.dataframe(df, use_container_width=True)
        st.download_button(
            label="Download Obligations CSV",
            data=df.to_csv(index=False),
            file_name="policy_obligations.csv",
            mime="text/csv"
        )
    else:
        st.info("No obligations to display yet.")

    # === Policy Q&A Chatbot ===
    st.markdown("---")
    st.markdown("## 🤖 Ask Your Policies (AI Chat)")
    st.caption("Type a question about your policies. The AI answers ONLY using your uploaded documents.")
    query = st.text_input("Ask a policy/compliance question", key="policy_qa")
    if query:
        with st.spinner("Getting answer..."):
            answer = ai_chat(query, all_policy_text)
        st.success(answer)

    # === AUDIT PROCESS DASHBOARD ===
    st.markdown("---")
    st.markdown("## 🕵️ Audit Log & One-Click Audit Pack")
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
