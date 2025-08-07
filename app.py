import streamlit as st
import streamlit_authenticator as stauth
import yaml
import PyPDF2
import os
from dotenv import load_dotenv
import openai
from db import SessionLocal, create_db, CouncilUser, PolicyDoc
import json
import pandas as pd

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

    # === DB SETUP ===
    create_db()
    db = SessionLocal()

    # --- Get or create council user in DB ---
    db_user = db.query(CouncilUser).filter_by(username=username).first()
    if not db_user:
        db_user = CouncilUser(username=username, name=name, email=config["credentials"]["usernames"][username]["email"])
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

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

    # --- Handle PDF Upload & AI Processing ---
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

            obligations_json = json.dumps(obligations_list)

            doc = PolicyDoc(
                filename=uploaded_file.name,
                summary=summary_part.strip(),
                obligations=obligations_json,
                user_id=db_user.id
            )
            db.add(doc)
            db.commit()
            st.success("Document and obligations saved to dashboard.")

    # --- DASHBOARD: Show Council's Docs ---
    st.markdown("## 🗂️ Uploaded Documents Dashboard")
    if username == "admin":
        user_docs = db.query(PolicyDoc).all()
        st.markdown("**(Admin: Viewing all councils)**")
    else:
        user_docs = db.query(PolicyDoc).filter_by(user_id=db_user.id).all()

    if user_docs:
        export_data = []
        for doc in user_docs:
            with st.expander(f"📄 {doc.filename}"):
                st.markdown(f"**Summary:**<br>{doc.summary}", unsafe_allow_html=True)
                st.markdown("**Obligations:**")
                obligations = json.loads(doc.obligations)
                for obligation in obligations:
                    st.markdown(f"- {'✅' if obligation.get('done') else '⬜️'} {obligation['text']}")
                # Collect for CSV
                for obligation in obligations:
                    export_data.append({
                        "Filename": doc.filename,
                        "Summary": doc.summary,
                        "Obligation": obligation["text"],
                        "Done": obligation.get("done", False),
                        "User": db_user.username if username != "admin" else "ALL"
                    })
        # Download CSV
        df = pd.DataFrame(export_data)
        st.download_button(
            label="Download CSV",
            data=df.to_csv(index=False),
            file_name="compliance_dashboard.csv",
            mime="text/csv"
        )
    else:
        st.info("No documents uploaded yet. Upload a policy PDF to begin.")

    st.markdown("---")
    st.caption("Built in Melbourne for Australian councils. Your documents are always safe and secure.")

else:
    st.stop()
