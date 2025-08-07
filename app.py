from db import SessionLocal, create_db, CouncilUser, PolicyDoc
import json

create_db()

import streamlit as st
import streamlit_authenticator as stauth
import yaml
import PyPDF2
import os
from dotenv import load_dotenv
import openai

# === AUTHENTICATION SETUP ===
with open("config.yaml") as file:
    config = yaml.safe_load(file)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status is False:
    st.error("Incorrect username or password")
elif authentication_status is None:
    st.warning("Please enter your username and password")
elif authentication_status:
    authenticator.logout("Logout", "sidebar")
    st.sidebar.write(f"Logged in as: {name} ({username})")

    # === APP STARTS HERE ===

    # --- Load OpenAI API key ---
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    openai.api_key = OPENAI_API_KEY

    st.set_page_config(page_title="PolicySimplify AI", page_icon="📄✅", layout="centered")

    # --- Branding ---
    st.markdown("""
    <div style="text-align:center;">
        <span style="font-size:2.6em;">📄✅</span>
        <h1 style="margin-bottom:0;">PolicySimplify AI</h1>
        <div style="font-size:1.13em; color:#1764a7; margin-bottom:18px;">
            Instantly simplify council compliance.<br>
            Upload a policy PDF. Instantly get an AI-powered summary, obligations, and compliance checklist.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Session state for uploaded docs (user-specific for now) ---
    if "docs" not in st.session_state:
        st.session_state.docs = []

    # --- PDF Upload ---
    uploaded_file = st.file_uploader("Upload PDF", type=["pdf"], help="Limit 200MB per file • PDF")

    def extract_pdf_text(pdf_file):
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text

    def get_ai_summary_and_obligations(text):
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
    {text[:6000]}
    \"\"\"
    """
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=700
        )
        return response.choices[0].message.content.strip()

    if uploaded_file:
        st.success("PDF uploaded successfully!")
        with st.spinner("Extracting text..."):
            pdf_text = extract_pdf_text(uploaded_file)
            st.text_area("Extracted Policy Text (demo)", pdf_text[:3000], height=180)
        if st.button("Generate AI Summary & Obligations"):
            with st.spinner("Talking to PolicySimplify AI..."):
                ai_response = get_ai_summary_and_obligations(pdf_text)

            # Split AI response into summary and obligations
            if "Obligations:" in ai_response:
                summary_part, obligations_part = ai_response.split("Obligations:", 1)
            else:
                summary_part = ai_response
                obligations_part = ""

            obligations_list = []
            for line in obligations_part.strip().split("\n"):
                if line.strip().startswith("-"):
                    obligations_list.append({"text": line.strip()[1:].strip(), "done": False})

            # Save to session_state
            st.session_state.docs.append({
                "filename": uploaded_file.name,
                "summary": summary_part.strip(),
                "obligations": obligations_list
            })

            st.success("Document and obligations saved to dashboard.")

    # --- Dashboard ---
    st.markdown("## 🗂️ Uploaded Documents Dashboard")

    if st.session_state.docs:
        for i, doc in enumerate(st.session_state.docs):
            with st.expander(f"📄 {doc['filename']}"):
                st.markdown(f"**Summary:**<br>{doc['summary']}", unsafe_allow_html=True)
                st.markdown("**Obligations:**")
                for j, obligation in enumerate(doc["obligations"]):
                    checked = st.checkbox(obligation["text"], value=obligation["done"], key=f"doc_{i}_obl_{j}")
                    doc["obligations"][j]["done"] = checked
    else:
        st.info("No documents uploaded yet. Upload a policy PDF to begin.")

    st.markdown("---")
    st.caption("Built in Melbourne for Australian councils. Your documents are always safe and secure.")

else:
    st.stop()
