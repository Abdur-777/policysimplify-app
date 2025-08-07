import streamlit as st
import PyPDF2
import os
from dotenv import load_dotenv
import openai

# Load OpenAI API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

st.set_page_config(page_title="PolicySimplify AI", page_icon="📄✅", layout="centered")
st.title("📄✅ PolicySimplify AI")
st.write("**Upload a policy PDF. Instantly get an AI-powered summary, obligations, and compliance checklist.**")

uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])

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
        st.text_area("Extracted Policy Text (demo)", pdf_text[:3000], height=220)
    if st.button("Generate AI Summary & Obligations"):
        with st.spinner("Talking to PolicySimplify AI..."):
            ai_response = get_ai_summary_and_obligations(pdf_text)
        st.markdown("---")
        st.markdown(f"### 🧠 AI-Powered Summary & Checklist\n\n{ai_response}")

else:
    st.info("Please upload a policy or regulation PDF to begin.")

st.markdown("---")
st.caption("Built in Melbourne for Australian councils. Your documents are always safe and secure.")
