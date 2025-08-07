import streamlit as st
import PyPDF2
import os

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

if uploaded_file:
    st.success("PDF uploaded successfully!")
    with st.spinner("Extracting text..."):
        pdf_text = extract_pdf_text(uploaded_file)
        st.text_area("Extracted Policy Text (for demo purposes)", pdf_text[:3000], height=300)
    st.info("**Next:** We’ll add the AI summary + compliance extraction tomorrow!")

else:
    st.info("Please upload a policy or regulation PDF to begin.")

st.markdown("---")
st.caption("Built in Melbourne for Australian councils. Your documents are always safe and secure.")
