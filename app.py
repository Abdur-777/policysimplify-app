import streamlit as st
import PyPDF2
import openai
import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict

# --- Branding/Config ---
COUNCIL_NAME = "Wyndham City Council"
COUNCIL_LOGO = "https://www.wyndham.vic.gov.au/themes/custom/wyndham/logo.png"
GOV_ICON = "https://cdn-icons-png.flaticon.com/512/3209/3209872.png"
COUNCIL_PIN = "4242"
SUPPORT_EMAIL = "civreplywyndham@gmail.com"

st.set_page_config(page_title="PolicySimplify AI", page_icon="✅", layout="centered")

# --- PIN LOGIN ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

def login_screen():
    st.markdown("""
    <style>
    .login-card {
        background:#fff;
        border-radius:28px;
        box-shadow:0 6px 36px #1764a740;
        max-width:420px;
        padding:40px 32px 30px 32px;
        margin:70px auto 36px auto;
        text-align:center;
    }
    .login-logo {
        display:flex;
        justify-content:center;
        align-items:center;
        gap:15px;
        margin-bottom:10px;
    }
    .login-title {
        font-size:2.25em;
        font-weight:900;
        color:#1764a7;
        letter-spacing:-1.2px;
    }
    .login-sub {
        color:#1976d2;
        font-size:1.12em;
        margin-top:5px;
        font-weight:600;
    }
    .ps-privacy {
        color:#222;
        font-size:1.01em;
        font-weight:400;
        margin-top:25px;
        background:#eaf7ef;
        border-radius:8px;
        padding:8px 10px 7px 10px;
        display:block;
    }
    </style>
    <div class='login-card'>
        <div class='login-logo'>
            <img src='%s' width='42'>
            <span class='login-title'>PolicySimplify AI</span>
            <img src='%s' width='46' style="border-radius:11px;box-shadow:0 1px 7px #1113;"/>
        </div>
        <div class='login-sub'>%s</div>
        <div style="margin-top:17px;color:#1966b2;">Enter Council Access PIN to continue</div>
    """ % (GOV_ICON, COUNCIL_LOGO, COUNCIL_NAME), unsafe_allow_html=True)
    pin = st.text_input("Council Access PIN", type="password")
    if st.button("Login"):
        if pin == COUNCIL_PIN:
            st.session_state["authenticated"] = True
            st.success("Access granted. Welcome!")
            st.rerun()
        else:
            st.error("Incorrect PIN. Please try again.")
    st.markdown("""
    <span class="ps-privacy">
        🔒 All information is <b>protected and private</b> under <b>Australian standards</b>.
    </span>
    </div>
    """, unsafe_allow_html=True)

if not st.session_state["authenticated"]:
    login_screen()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:13px; margin-bottom: 18px;">
            <img src="{COUNCIL_LOGO}" width="54" style="border-radius:13px;box-shadow:0 1px 8px #1112;"/>
            <div style="font-size:1.24em; font-weight:700; color:#1565c0;">{COUNCIL_NAME}</div>
        </div>
        """, unsafe_allow_html=True
    )
    st.markdown("""
        <style>
        .sidebar-link {
            display: block;
            padding: 10px 0 8px 0;
            color: #1565c0;
            font-size: 1.08em;
            font-weight: 500;
            border-radius: 6px;
            text-decoration: none;
        }
        .sidebar-link:hover {
            background: #e3f2fd;
        }
        </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="sidebar-link" style="background:#e3f2fd;"><span style="vertical-align:-2px;">📄</span> Policy Upload</div>', unsafe_allow_html=True)
    st.markdown('<a class="sidebar-link" href="#reminders">⏰ Reminders</a>', unsafe_allow_html=True)
    st.markdown('<a class="sidebar-link" href="#dashboard">📊 Dashboard</a>', unsafe_allow_html=True)
    st.markdown('<a class="sidebar-link" href="#usage">📈 Usage</a>', unsafe_allow_html=True)
    st.markdown('<a class="sidebar-link" href="#audit-log">🕵️ Audit Log</a>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Feedback or support?**")
    st.markdown(
        f"<a href='mailto:{SUPPORT_EMAIL}?subject=PolicySimplify%20AI%20Support' target='_blank' style='text-decoration:none;'><button style='background:#1764a7;color:white;padding:6px 16px;border:none;border-radius:9px;margin-top:6px;cursor:pointer;font-size:1em;'>Contact Support</button></a>",
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.caption("🔒 All data stored securely in Australia.")

# --- HERO HEADER ---
st.markdown("""
<style>
.hero-card {
  background: linear-gradient(90deg, #1966b2 0%, #44bbff 100%);
  color: #fff;
  border-radius: 30px;
  box-shadow: 0 4px 24px #1966b230;
  padding: 36px 24px 28px 24px;
  margin-bottom: 40px;
  text-align: center;
  max-width: 680px;
  margin-left: auto;
  margin-right: auto;
}
.hero-row {display:flex; align-items:center; justify-content:center; gap:18px;}
.hero-title {font-size:2.55em; font-weight:900; letter-spacing:-1.5px; margin:0;}
.hero-sub {font-size:1.21em; color:#e3f2fd; font-weight:400; margin-bottom:2px;}
</style>
<div class="hero-card">
  <div class="hero-row">
    <img src="%s" width="42"/>
    <span class="hero-title">PolicySimplify AI</span>
    <img src="%s" width="53" style="border-radius:12px;box-shadow:0 1px 9px #1112;"/>
  </div>
  <div class="hero-sub">Council: <b>Wyndham City Council</b></div>
  <div style="font-size:1.07em; margin:14px 0 0 0;">Upload council policies & instantly see what matters.<br>
  <span style="color:#d2ffad;">Australian-hosted • Secure • Unlimited uploads</span></div>
</div>
""" % (GOV_ICON, COUNCIL_LOGO), unsafe_allow_html=True)

# --- UPLOAD CARD (themed upload zone) ---
st.markdown("""
<style>
.upload-card {
    background: #fff;
    border-radius: 24px;
    box-shadow: 0 2px 16px #1764a722;
    padding: 32px 30px 20px 30px;
    margin: 0 auto 30px auto;
    max-width: 500px;
    min-width: 320px;
    text-align: center;
}
.upload-title {
    font-size: 1.45em;
    font-weight: 600;
    color: #1764a7;
    margin-bottom: 10px;
    letter-spacing: -.02em;
}
.upload-sub {
    font-size: 1em;
    color: #337cc3;
    margin-bottom: 20px;
}
.upload-icon {
    font-size: 2.6em;
    margin-bottom: 2px;
}
</style>
<div class="upload-card">
    <div class="upload-icon">📤</div>
    <div class="upload-title">Upload Policy PDF(s)</div>
    <div class="upload-sub">Drag & drop or click to select policy documents.<br>
    <span style="color:#59c12a;">Max 200MB each • PDF only</span></div>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader("", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
st.markdown("---")

# --- API Keys ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- Session State ---
for k, v in {
    'obligations': {}, 'audit_log': [], 'search_text': "",
    'recent_uploads': [], 'usage': defaultdict(int)
}.items():
    if k not in st.session_state: st.session_state[k] = v

def extract_pdf_text(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    return "".join([page.extract_text() or "" for page in pdf_reader.pages])

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

if uploaded_files:
    all_policy_text = ""
    dashboard_data = []
    for uploaded_file in uploaded_files:
        pdf_text = extract_pdf_text(uploaded_file)
        all_policy_text += "\n\n" + pdf_text

        # Usage Analytics
        st.session_state['usage']['uploads'] += 1

        # Recent Uploads
        uploaded = any(entry['filename'] == uploaded_file.name for entry in st.session_state['recent_uploads'])
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
                    "who": "You",
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                })

    # Reminders Bar
    st.markdown("### ⏰ Reminders")
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

    # Full-Text Search
    st.markdown("---")
    st.markdown("### 🔍 Full-Text Search")
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

    # Recent Uploads Section
    st.markdown("---")
    st.markdown("""
    <style>
    .recent-uploads-card {
        background: #fff;
        border-radius: 19px;
        box-shadow: 0 2px 13px #1966b210;
        padding: 25px 25px 14px 25px;
        margin: 0 auto 30px auto;
        max-width: 520px;
        min-width: 300px;
    }
    .recent-uploads-title {
        font-size: 1.23em;
        font-weight: 700;
        color: #1565c0;
        margin-bottom: 8px;
        letter-spacing: -.01em;
    }
    .recent-upload-filename {
        color: #1966b2;
        font-weight: 500;
        font-size: 1.07em;
    }
    </style>
    <div class="recent-uploads-card">
        <div class="recent-uploads-title">📂 Recent Uploads</div>
    """, unsafe_allow_html=True)
    recent_uploads = st.session_state['recent_uploads'][:10]
    if recent_uploads:
        for item in recent_uploads:
            fname, uploaded_at = item['filename'], item['uploaded_at']
            st.markdown(
                f"<span class='recent-upload-filename'>• {fname}</span> &nbsp; "
                f"<span style='color:#388e3c;font-size:0.96em;'>uploaded {uploaded_at}</span>",
                unsafe_allow_html=True
            )
    else:
        st.info("No uploads yet. Your recently uploaded files will appear here.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Visual Obligation Cards (Compliance Dashboard)
    st.markdown("---")
    st.markdown("""
    <style>
    .ob-card {background:#fff;border-radius:18px;box-shadow:0 2px 14px #1966b222;margin-bottom:20px;padding:22px 22px 16px 22px;}
    .ob-title {font-size:1.09em; font-weight:600; color:#1966b2;}
    .ob-done {color:#59c12a; font-weight:700;}
    .ob-chip {display:inline-block; background:#e3f2fd; color:#1764a7; border-radius:9px; padding:2px 11px 3px 11px; margin-right:7px; font-size:0.97em;}
    .ob-overdue {background:#e65c5c; color:#fff;}
    .ob-upcoming {background:#f3c852; color:#444;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 📊 Compliance Dashboard (Card View)")
    for fname, doc in st.session_state['obligations'].items():
        st.markdown(f"<div class='ob-title'>📑 {fname}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-bottom:8px;color:#1565c0;font-size:1.06em;'><b>Summary:</b> {doc['summary']}</div>", unsafe_allow_html=True)
        for idx, obl in enumerate(doc["obligations"]):
            color = get_deadline_color(obl.get("deadline", ""))
            chip_class = "ob-chip"
            if color == "#e65c5c":
                chip_class += " ob-overdue"
            elif color == "#f3c852":
                chip_class += " ob-upcoming"
            status_icon = "✅" if obl['done'] else "⬜️"
            st.markdown(
                f"""
                <div class="ob-card">
                    <span style="font-size:1.23em;">{status_icon}</span>
                    <b style="margin-left:7px;">{obl['text']}</b><br>
                    <span class="{chip_class}">{'Overdue' if color=='#e65c5c' else ('Due soon' if color=='#f3c852' else 'Deadline')}</span>
                    <span class="ob-chip">{obl.get('deadline', '')}</span>
                    <span class="ob-chip" style="background:#e3ffd6;color:#388e3c;">Assigned: {obl.get('assigned_to','')}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    # POLICY Q&A CHAT
    st.markdown("---")
    st.markdown("## 🤖 Ask Your Policies (AI Chat)")
    st.caption("Type a question about your policies. The AI answers ONLY using your uploaded documents.")
    query = st.text_input("Ask a policy/compliance question", key="policy_qa")
    if query:
        st.session_state['usage']['qa'] += 1
        with st.spinner("Getting answer..."):
            answer = ai_chat(query, all_policy_text)
        st.success(answer)

    # AUDIT LOG
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

    # USAGE ANALYTICS
    st.markdown("---")
    st.markdown("## 📈 Usage Analytics")
    usage = st.session_state['usage']
    st.metric("Policy PDFs Uploaded", usage["uploads"])
    st.metric("AI Policy Q&As", usage["qa"])
    st.caption("Counts reset on server restart. For advanced usage, connect to a database.")

else:
    st.info("Upload one or more council policy PDFs to begin.")

st.markdown("---")
st.markdown("""
<span style='color: #59c12a; font-weight:bold;'>PolicySimplify AI – Built for Australian councils. All data hosted securely in Australia.</span>
""", unsafe_allow_html=True)
