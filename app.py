import streamlit as st
import PyPDF2
import openai
import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
import base64

# =========================
# CONFIG + MULTI-COUNCIL
# =========================

COUNCILS = [
    {
        "name": "Wyndham City Council",
        "logo": "https://www.wyndham.vic.gov.au/themes/custom/wyndham/logo.png",
        "color": "#1565c0",
        "gradient": "linear-gradient(90deg, #1966b2 0%, #44bbff 100%)"
    },
    {
        "name": "Council Whyndah",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/5/5f/City_of_Whyndah_logo.png",
        "color": "#139496",
        "gradient": "linear-gradient(90deg, #0e7a6f 0%, #32c4a7 100%)"
    }
]
GOV_ICON = "https://cdn-icons-png.flaticon.com/512/3209/3209872.png"
LANGUAGES = {"English":"en", "简体中文":"zh", "Español":"es"}
DEFAULT_LANG = "English"

# =========================
# SESSION STATE
# =========================

if "council_idx" not in st.session_state:
    st.session_state["council_idx"] = 0
if "obligations" not in st.session_state:
    st.session_state["obligations"] = {}
if "audit_log" not in st.session_state:
    st.session_state["audit_log"] = []
if "search_text" not in st.session_state:
    st.session_state["search_text"] = ""
if "recent_uploads" not in st.session_state:
    st.session_state["recent_uploads"] = []
if "dark_mode" not in st.session_state:
    st.session_state["dark_mode"] = False
if "show_onboarding" not in st.session_state:
    st.session_state["show_onboarding"] = True
if "feedback" not in st.session_state:
    st.session_state["feedback"] = {}
if "autosaved" not in st.session_state:
    st.session_state["autosaved"] = True
if "user_name" not in st.session_state:
    st.session_state["user_name"] = "You"
if "user_avatar" not in st.session_state:
    st.session_state["user_avatar"] = ""
if "recent_qa" not in st.session_state:
    st.session_state["recent_qa"] = []
if "language" not in st.session_state:
    st.session_state["language"] = DEFAULT_LANG
if "admin_pin" not in st.session_state:
    st.session_state["admin_pin"] = ""
if "show_admin" not in st.session_state:
    st.session_state["show_admin"] = False
if "show_disclaimer" not in st.session_state:
    st.session_state["show_disclaimer"] = True

def council():
    return COUNCILS[st.session_state['council_idx']]

# =========================
# PAGE STYLING
# =========================

primary_color = council()["color"]
gradient = council()["gradient"]
bg_color = "#eaf3fa" if not st.session_state["dark_mode"] else "#131924"
txt_color = "#1966b2" if not st.session_state["dark_mode"] else "#f4f4f4"
alt_bg = "#fff" if not st.session_state["dark_mode"] else "#1b2537"

st.set_page_config(page_title="PolicySimplify AI", page_icon="✅", layout="centered")
st.markdown(f"""
    <style>
    body, .stApp {{ background-color: {bg_color}; }}
    .main {{ background-color: {bg_color}; }}
    .reportview-container {{ background-color: {bg_color}; }}
    html, body, input, textarea {{ font-size: 18px !important; }}
    .inline-help {{
        color: #2687e6;
        background: #d6eeff;
        border-radius: 9px;
        font-size: 0.97em;
        padding: 1px 9px;
        margin-left: 6px;
        cursor: help;
        border: 1px solid #92cfff;
    }}
    </style>
""", unsafe_allow_html=True)

# =========================
# ADMIN & PRIVACY POPUP
# =========================

if st.session_state["show_disclaimer"]:
    st.warning("By uploading files, you confirm your right to handle council data and agree to our Privacy & Compliance Policy.", icon="🔒")
    if st.button("I Understand", key="close_disclaimer"):
        st.session_state["show_disclaimer"] = False

def admin_panel():
    st.header("🔑 Admin Feedback Dashboard")
    feedback_list = []
    for fname, doc in st.session_state['obligations'].items():
        for idx, obl in enumerate(doc["obligations"]):
            k = f"{fname}-{idx}"
            fb = st.session_state['feedback'].get(k, None)
            if fb is not None:
                feedback_list.append({"File":fname, "Obligation":obl["text"], "Feedback":"👍" if fb else "👎"})
    if feedback_list:
        st.dataframe(pd.DataFrame(feedback_list))
    else:
        st.info("No feedback yet.")
    st.info("This dashboard is only visible after entering the admin PIN.")

if st.session_state["show_admin"]:
    admin_panel()

# =========================
# SIDEBAR
# =========================

with st.sidebar:
    if st.button("🌙" if not st.session_state["dark_mode"] else "☀️", help="Toggle dark mode"):
        st.session_state["dark_mode"] = not st.session_state["dark_mode"]
        st.experimental_rerun()
    st.selectbox("Switch Council", [c["name"] for c in COUNCILS], index=st.session_state['council_idx'],
                 key="council_idx", on_change=lambda: st.experimental_rerun())
    st.selectbox("🌏 Language", list(LANGUAGES.keys()), index=list(LANGUAGES.keys()).index(st.session_state["language"]), key="language")
    # User settings
    st.text_input("Display Name", value=st.session_state["user_name"], key="user_name")
    user_avatar = st.text_input("Profile Photo URL (optional)", value=st.session_state["user_avatar"])
    if user_avatar:
        st.session_state["user_avatar"] = user_avatar
        st.markdown(f"<img src='{user_avatar}' width='54' style='border-radius:99px;box-shadow:0 1px 8px #1112; margin: 3px 0;'/>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom: 18px;">
            <img src="{council()['logo']}" width="54" style="border-radius:13px;box-shadow:0 1px 8px #1112;"/>
            <div style="font-size:1.24em; font-weight:700; color:{primary_color};">{council()['name']}</div>
        </div>
        """, unsafe_allow_html=True
    )
    st.markdown('<div class="sidebar-link" style="background:#e3f2fd;"><span style="vertical-align:-2px;">📄</span> Policy Upload</div>', unsafe_allow_html=True)
    st.markdown('<a class="sidebar-link" href="#reminders">⏰ Reminders</a>', unsafe_allow_html=True)
    st.markdown('<a class="sidebar-link" href="#dashboard">📊 Dashboard</a>', unsafe_allow_html=True)
    st.markdown('<a class="sidebar-link" href="#audit-log">🕵️ Audit Log</a>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Feedback or support?**")
    st.markdown(
        "<a href='mailto:civreplywyndham@gmail.com?subject=PolicySimplify%20AI%20Support' target='_blank' style='text-decoration:none;'><button style='background:#1764a7;color:white;padding:6px 16px;border:none;border-radius:9px;margin-top:6px;cursor:pointer;font-size:1em;'>Contact Support</button></a>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    # Step 29: Admin Feedback Dashboard PIN
    admin = st.text_input("🔑 Admin PIN", type="password", key="admin_pin_input")
    if admin == "8888":  # Change PIN as needed
        st.session_state["show_admin"] = True
    st.caption("🔒 All data stored securely in Australia.")

# =========================
# HERO HEADER
# =========================

st.markdown(f"""
<style>
.hero-container {{
    margin: 38px auto 0 auto;
    max-width: 730px;
}}
.hero-card {{
    background: {gradient};
    color: #fff;
    border-radius: 32px;
    box-shadow: 0 4px 32px #1966b228;
    padding: 36px 54px 26px 54px;
    margin-bottom: 42px;
    text-align: left;
    min-width: 320px;
}}
.hero-row {{
    display: flex; align-items: center; gap: 26px; flex-wrap: wrap;
}}
.hero-title {{
    font-size: 2.50em; font-weight: 900; letter-spacing: -1px; color: #fff; display: flex; align-items: center; gap: 16px;
}}
.hero-ai-flare {{
    margin-left: 3px; display: inline-block; width: 15px; height: 15px;
    background: radial-gradient(circle at 60% 35%, #9cffc6 0%, #16c78b 85%, #00817a 100%);
    border-radius: 50%;
    animation: flarePulse 1.3s infinite alternate;
    box-shadow: 0 0 8px 3px #b2f7d1b0;
}}
@keyframes flarePulse {{
    0% {{ box-shadow: 0 0 6px 2px #b2f7d1b0;}}
    100% {{ box-shadow: 0 0 16px 4px #91f5b1b7;}}
}}
.hero-sub {{ font-size: 1.16em; color: #e3f2fd; font-weight: 400; margin-bottom: 4px; margin-top: 2px; }}
@media (max-width:650px){{.hero-card{{padding:14px 8px 18px 8px;}} .hero-title{{font-size:1.17em;}}}}
</style>
<div class="hero-container">
<div class="hero-card">
    <div class="hero-row">
        <img src="{GOV_ICON}" width="54" height="54" style="border-radius:18px;box-shadow:0 2px 12px #1579c099;object-fit:cover;" class="hero-icon-bounce" alt="Book Icon"/>
        <div>
            <div class="hero-title">
                PolicySimplify AI <span class="hero-ai-flare" title="AI-powered"></span>
            </div>
            <div class="hero-sub"><b>Council:</b> {council()['name']}</div>
            <div style="font-size:1.02em; margin:4px 0 0 0;color:#eafff3;">
                Upload council policies & instantly see what matters.<br>
                <span style="color:#e4ffd7;font-weight:500;">Australian-hosted • Secure • Unlimited uploads</span>
            </div>
        </div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

# =========================
# ONBOARDING
# =========================

if st.session_state["show_onboarding"]:
    st.info("👋 Welcome! Start by uploading a council policy PDF, then click the ‘?’ icons for help at any time.", icon="👋")
    if st.button("Got it! Hide this tip", key="hide_onboard"):
        st.session_state["show_onboarding"] = False
        st.experimental_rerun()

# =========================
# UPLOAD ZONE (w/help)
# =========================

st.markdown(f"""
<div class="upload-card" aria-label="Upload area" style="background:{alt_bg};">
    <div class="upload-icon">📥</div>
    <div class="upload-title">
        Upload Policy PDF(s)
        <span class="inline-help" title="Step 1: Upload one or more council policy PDFs. Only PDF, max 200MB each.">?</span>
    </div>
    <div class="upload-sub" style="color:#388e3c;">
        Drag & drop or click to select policy documents.<br>
        <span style="color:#4caf50;">Max 200MB each • PDF only</span>
    </div>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

st.markdown("---")

# =========================
# SHARE BUTTON
# =========================

st.markdown("""
<div style="margin-bottom:16px;">
    <button onclick="navigator.clipboard.writeText(window.location.href);alert('Page URL copied!')" style="background:#1764a7;color:white;padding:7px 19px;border:none;border-radius:9px;margin-right:10px;cursor:pointer;font-size:1em;">🔗 Share this tool</button>
</div>
""", unsafe_allow_html=True)

# =========================
# LOAD OPENAI KEY
# =========================

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# =========================
# HELPERS
# =========================

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
   - If no deadline, suggest one if appropriate (e.g., "every year", "within 30 days")
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

def get_deadline_color(deadline_str):
    if not deadline_str: return "#eaf3fa"
    try:
        if "within" in deadline_str or "every" in deadline_str:
            return "#f3c852"
        date = pd.to_datetime(deadline_str, errors="coerce")
        if pd.isnull(date): return "#eaf3fa"
        today = pd.Timestamp.now()
        if date < today:
            return "#e65c5c"
        elif (date - today).days <= 7:
            return "#f3c852"
    except:
        return "#eaf3fa"
    return "#eaf3fa"

def pdf_download_button(summary, obligations, filename="PolicySimplify_Summary.pdf"):
    """ Step 24: Export as PDF """
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, "PolicySimplify AI Summary", ln=1)
    pdf.set_font("Arial", "", 12)
    pdf.multi_cell(0, 10, f"Summary:\n{summary}\n")
    pdf.cell(0, 12, "Obligations:", ln=1)
    for o in obligations:
        pdf.multi_cell(0, 8, "- "+o["text"])
    pdf_file = f"/tmp/{filename}"
    pdf.output(pdf_file)
    with open(pdf_file, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.download_button("⬇️ Download summary as PDF", f"data:application/pdf;base64,{b64}", file_name=filename)

# =========================
# MAIN LOGIC
# =========================

if uploaded_files:
    all_policy_text = ""
    dashboard_data = []
    for uploaded_file in uploaded_files:
        # Step 28: File validation
        if not uploaded_file.name.lower().endswith(".pdf"):
            st.error(f"❌ {uploaded_file.name} is not a PDF. Please upload PDF files only.")
            continue
        pdf_text = extract_pdf_text(uploaded_file)
        all_policy_text += "\n\n" + pdf_text

        uploaded = any(
            entry['filename'] == uploaded_file.name
            for entry in st.session_state['recent_uploads']
        )
        if not uploaded:
            st.session_state['recent_uploads'].insert(0, {
                "filename": uploaded_file.name,
                "uploaded_at": datetime.now().strftime('%Y-%m-%d %H:%M')
            })
        st.session_state['recent_uploads'] = st.session_state['recent_uploads'][:10]

        if uploaded_file.name not in st.session_state['obligations']:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                ai_response = ai_summarize(pdf_text)
                summary_part, obligations_part = ai_response.split("Obligations:", 1) if "Obligations:" in ai_response else (ai_response, "")
                obligations_list = []
                for line in obligations_part.strip().split("\n"):
                    if line.strip().startswith("-"):
                        text = line.strip()[1:].strip()
                        deadline = ""
                        for kw in ["by ", "before ", "within ", "every ", "on ", "due ", "deadline:"]:
                            if kw in text.lower():
                                deadline = text[text.lower().find(kw):]
                                break
                        obligations_list.append({
                            "text": text,
                            "done": False,
                            "assigned_to": "",
                            "deadline": deadline,
                            "timestamp": None
                        })
                st.session_state['obligations'][uploaded_file.name] = {
                    "summary": summary_part.strip(),
                    "obligations": obligations_list
                }
                st.session_state['audit_log'].append({
                    "action": "upload",
                    "file": uploaded_file.name,
                    "obligation": "",
                    "who": st.session_state["user_name"],
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                })

    # ===== STEP 20: INLINE HELP =====
    st.markdown("""
    <span class="inline-help" title="Use reminders to catch overdue or upcoming deadlines.">?</span>
    """, unsafe_allow_html=True)

    # ===== STEP 21: END-USER SETTINGS =====
    st.markdown(f"<span style='font-size:1.08em;color:#1565c0;'>Hi, {st.session_state['user_name']}!</span>", unsafe_allow_html=True)

    # ===== STEP 22: PER-COUNCIL BRANDING (ALREADY DONE) =====

    # ===== STEP 23: FEEDBACK ON SUMMARY/OBLIGATIONS =====
    st.markdown("#### 📥 Feedback (click 👍 or 👎 on any obligation card below)")
    
    # ===== STEP 24: PDF EXPORT BUTTON (per policy) =====
    for fname, doc in st.session_state['obligations'].items():
        pdf_download_button(doc["summary"], doc["obligations"], filename=f"{fname}_summary.pdf")

    # ===== STEP 25: RECENT Q&A SIDEBAR =====
    st.markdown("### Recent Q&A")
    for q, a in st.session_state["recent_qa"][-5:][::-1]:
        st.markdown(f"<b>Q:</b> {q}<br><b>A:</b> {a}", unsafe_allow_html=True)

    # ===== STEP 26: MULTI-LANGUAGE UI (UI ONLY, NOT LLM) =====
    if st.session_state["language"] != "English":
        st.info("🌏 Language switching is UI only; LLM answers remain in English for now.")

    # ===== STEP 27: MOBILE FLOATING BAR =====
    st.markdown("""
    <style>
    @media (max-width:700px){
        .floatbar{
            display:block; position:fixed; bottom:28px; left:0; right:0; z-index:1000;
            background:#fff; box-shadow:0 2px 18px #1764a722; border-radius:15px;
            max-width:360px;margin:0 auto; text-align:center; padding:8px 12px;
        }
        .floatbar button{margin:0 8px;}
    }
    </style>
    <div class="floatbar" style="display:none">
        <button onclick="window.scrollTo(0,0)">⬆️ Upload</button>
        <button onclick="window.scrollTo(0,document.body.scrollHeight/2)">💬 Chat</button>
        <button onclick="window.scrollTo(0,document.body.scrollHeight)">🕵️ Audit</button>
    </div>
    """, unsafe_allow_html=True)

    # ===== STEP 28: FILE TYPE VALIDATION (already above) =====

    # ===== STEP 29: ADMIN FEEDBACK DASHBOARD (in sidebar, PIN: 8888) =====

    # ===== STEP 30: PRIVACY/COMPLIANCE DISCLAIMER (top) =====

    # === REMINDERS BAR ===
    st.markdown("### ⏰ Reminders <span class='inline-help' title='See all overdue and upcoming obligations.'>?</span>", unsafe_allow_html=True)
    reminder_count, upcoming_count = 0, 0
    for fname, doc in st.session_state['obligations'].items():
        for obl in doc["obligations"]:
            color = get_deadline_color(obl.get("deadline", ""))
            if color == "#e65c5c":
                st.markdown(f'<span class="reminder">Overdue:</span> <b>{obl["text"]}</b>', unsafe_allow_html=True)
                reminder_count += 1
            elif color == "#f3c852":
                st.markdown(f'<span class="reminder-upcoming">Due Soon:</span> <b>{obl["text"]}</b>', unsafe_allow_html=True)
                upcoming_count += 1
    if reminder_count == 0 and upcoming_count == 0:
        st.info("No overdue or upcoming deadlines!")

    # === FULL-TEXT SEARCH ===
    st.markdown("---")
    st.markdown("### 🔍 Full-Text Search <span class='inline-help' title='Search obligations, summaries, and policies.'>?</span>", unsafe_allow_html=True)
    search_text = st.text_input("Search all obligations, summaries, and policies...", key="search")
    st.session_state['search_text'] = search_text
    dashboard_data = []
    for fname, doc in st.session_state['obligations'].items():
        for obl in doc["obligations"]:
            match = (
                (search_text.lower() in obl["text"].lower() if search_text else True) or
                (search_text.lower() in doc["summary"].lower() if search_text else True)
            )
            if match:
                dashboard_data.append({
                    "Filename": fname,
                    "Summary": doc["summary"][:100]+"..." if len(doc["summary"]) > 100 else doc["summary"],
                    "Obligation": obl["text"],
                    "Done": "✅" if obl['done'] else "⬜️",
                    "Assigned to": obl.get("assigned_to",""),
                    "Deadline": obl.get("deadline",""),
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
        st.info("No matching obligations found.")

    # === COMPLIANCE DASHBOARD (CARD VIEW) ===
    st.markdown("---")
    st.markdown("## 📊 Compliance Dashboard (Card View) <span class='inline-help' title='Click the checkboxes to mark obligations as done.'>?</span>", unsafe_allow_html=True)
    for fname, doc in st.session_state['obligations'].items():
        st.markdown(f"<div class='ob-title'>📑 {fname}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-bottom:8px;color:{primary_color};font-size:1.06em;'><b>Summary:</b> {doc['summary']}</div>", unsafe_allow_html=True)
        for idx, obl in enumerate(doc["obligations"]):
            color = get_deadline_color(obl.get("deadline", ""))
            chip_class = "ob-chip"
            if color == "#e65c5c":
                chip_class += " ob-overdue"
            elif color == "#f3c852":
                chip_class += " ob-upcoming"
            status_icon = "✅" if obl['done'] else "⬜️"
            # Inline feedback
            k = f"{fname}-{idx}"
            fb = st.session_state['feedback'].get(k, None)
            fb_btn = ""
            if fb is not None:
                fb_btn = f"<span style='font-size:1.3em;'>{'👍' if fb else '👎'}</span>"
            if st.button(f"👍", key=f"thumbsup_{fname}_{idx}"):
                st.session_state['feedback'][k] = True
            if st.button(f"👎", key=f"thumbsdown_{fname}_{idx}"):
                st.session_state['feedback'][k] = False
            st.markdown(
                f"""
                <div class="ob-card">
                    <span style="font-size:1.23em;">{status_icon}</span>
                    <b style="margin-left:7px;">{obl['text']}</b><br>
                    <span class="{chip_class}">{'Overdue' if color=='#e65c5c' else ('Due soon' if color=='#f3c852' else 'Deadline')}</span>
                    <span class="ob-chip">{obl.get('deadline', '')}</span>
                    <span class="ob-chip" style="background:#e3ffd6;color:#388e3c;">Assigned: {obl.get('assigned_to','')}</span>
                    {fb_btn}
                </div>
                """,
                unsafe_allow_html=True
            )

    # === POLICY Q&A CHAT ===
    st.markdown("---")
    st.markdown("## 🤖 Ask Your Policies (AI Chat) <span class='inline-help' title='Ask a question about your uploaded policies.'>?</span>", unsafe_allow_html=True)
    query = st.text_input("Ask a policy/compliance question", key="policy_qa")
    if query:
        with st.spinner("Getting answer..."):
            answer = ai_chat(query, all_policy_text)
        st.success(answer)
        # Add to recent Q&A
        st.session_state["recent_qa"].append((query, answer))
        st.session_state["recent_qa"] = st.session_state["recent_qa"][-12:]  # Only last 12

    # === AUDIT LOG ===
    st.markdown("---")
    st.markdown("## 🕵️ Audit Log <span class='inline-help' title='See all actions for compliance.'>?</span>", unsafe_allow_html=True)
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
st.markdown(f"""
<span style='color: #59c12a; font-weight:bold;'>PolicySimplify AI – Built for Australian councils. All data hosted securely in Australia.</span>
""", unsafe_allow_html=True)
