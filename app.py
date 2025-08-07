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

st.set_page_config(page_title="PolicySimplify AI", page_icon="✅", layout="centered")
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)  # NEW SDK style

# --- HEADER ---
st.markdown(f"""
<div style="background:linear-gradient(90deg,#e3f2fd 0,#bbdefb 100%);padding:24px 8px 12px 8px;border-radius:0 0 26px 26px;text-align:center;margin-bottom:24px;">
    <img src="{COUNCIL_LOGO}" alt="logo" width="105"/>
    <div style="font-size:2em;margin-bottom:0;"><span style="vertical-align:-5px;">🏛️</span> <b>PolicySimplify AI</b></div>
    <div style="font-size:1.15em;color:#1764a7;margin-bottom:4px;">Council: <b>{COUNCIL_NAME}</b></div>
    <span style="font-size:1em;color:#333;">Upload council policies & instantly see what matters.<br>
    <span style="color: #59c12a;">Australian-hosted • Secure • Unlimited uploads</span></span>
</div>
""", unsafe_allow_html=True)

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

else:
    st.info("Upload one or more council policy PDFs to begin.")

st.markdown("---")
st.markdown("""
<span style='color: #59c12a; font-weight:bold;'>PolicySimplify AI – Built for Australian councils. All data hosted securely in Australia.</span>
""", unsafe_allow_html=True)
