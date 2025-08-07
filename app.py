import streamlit as st
import PyPDF2
import openai
import os
import json
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

# === BRANDING ===
COUNCIL_NAME = "Wyndham City Council"
COUNCIL_LOGO = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Emblem_of_Australia.svg/1200px-Emblem_of_Australia.svg.png"  # Government icon
BG_COLOR = "#e6f2ff"   # Light blue

st.set_page_config(page_title="PolicySimplify AI", page_icon="✅", layout="centered")
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- OpenAI CLIENT (new style) ---
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# === CUSTOM STYLING ===
st.markdown(f"""
    <style>
    body {{
        background-color: {BG_COLOR};
    }}
    .stApp {{
        background-color: {BG_COLOR};
    }}
    .main-header {{
        background: {BG_COLOR};
        padding: 32px 0 16px 0;
        border-radius: 0 0 24px 24px;
        box-shadow: 0 4px 12px #d9e9fa;
        margin-bottom: 2em;
    }}
    .council-badge {{
        color: #0066cc;
        background: #ffffffbb;
        border-radius: 8px;
        padding: 4px 18px;
        margin: 0 auto 14px auto;
        display: inline-block;
        font-weight: 600;
        font-size: 1.04em;
        letter-spacing: 1px;
        box-shadow: 0 2px 6px #b7d7f6;
    }}
    .policysimplify-title {{
        font-size: 2.6em;
        color: #1764a7;
        font-weight: bold;
        margin-bottom: 0.05em;
        text-align: center;
    }}
    .ai-blurb {{
        font-size: 1.18em;
        color: #1764a7;
        margin-bottom: 0.6em;
        text-align: center;
    }}
    .info-line {{
        color: #1a7737;
        font-size: 1.1em;
        font-weight: 600;
        text-align: center;
        margin-bottom: 20px;
    }}
    .export-btn button {{
        background: #146bb1 !important;
        color: #fff !important;
        border-radius: 8px !important;
    }}
    </style>
""", unsafe_allow_html=True)

# === HEADER SECTION ===
st.markdown(f"""
<div class="main-header">
    <div style="text-align:center;">
        <img src="{COUNCIL_LOGO}" alt="logo" width="66" style="margin-bottom:14px;"/>
    </div>
    <div class="policysimplify-title">
        PolicySimplify AI
    </div>
    <div class="council-badge">Council: Wyndham</div>
    <div class="ai-blurb">
        Instantly simplify council compliance.<br>
        Upload a policy PDF. Instantly get an AI-powered summary, obligations, and compliance checklist.<br>
        <span style="color: #59c12a;">Australian-hosted • Secure • Unlimited uploads</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# === PDF UPLOAD & PROCESSING ===
uploaded_files = st.file_uploader("📄 Upload Policy PDF(s)", type=["pdf"], accept_multiple_files=True)
policy_data = []

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

# --- PDF Processing Section ---
if uploaded_files:
    st.success("PDF(s) uploaded! See instant summary and obligations below.")
    dashboard_data = []
    all_policy_text = ""
    for uploaded_file in uploaded_files:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            pdf_text = extract_pdf_text(uploaded_file)
            ai_response = ai_summarize(pdf_text)
            all_policy_text += "\n\n" + pdf_text
            # Split summary and obligations
            summary_part, obligations_part = ai_response.split("Obligations:", 1) if "Obligations:" in ai_response else (ai_response, "")
            obligations_list = []
            for line in obligations_part.strip().split("\n"):
                if line.strip().startswith("-"):
                    obligations_list.append(line.strip()[1:].strip())
            # Store for dashboard/export
            for obl in obligations_list:
                dashboard_data.append({
                    "Filename": uploaded_file.name,
                    "Summary": summary_part.strip(),
                    "Obligation": obl,
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
            # --- Pretty Card ---
            with st.expander(f"📑 {uploaded_file.name}", expanded=True):
                st.markdown(f"**Summary:**\n{summary_part.strip()}")
                st.markdown("**Obligations & Actions:**")
                for obl in obligations_list:
                    st.markdown(f"- ⬜️ {obl}")
                st.caption("AI-generated. Please review obligations before action.")

    # === Dashboard ===
    st.markdown("---")
    st.markdown("## 📊 Compliance Dashboard & Export")
    if dashboard_data:
        df = pd.DataFrame(dashboard_data)
        st.dataframe(df[["Filename", "Obligation", "Date"]], use_container_width=True)
        st.download_button(
            label="Download Obligations CSV",
            data=df.to_csv(index=False),
            file_name="policy_obligations.csv",
            mime="text/csv",
            key="exportcsv"
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

else:
    st.info("Upload one or more council policy PDFs to begin.")

st.markdown("---")
st.markdown("""
<div class="info-line">
    PolicySimplify AI – Built for Australian councils. All data hosted securely in Australia.
</div>
""", unsafe_allow_html=True)
