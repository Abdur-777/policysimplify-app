import streamlit as st
import PyPDF2
import openai
import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime
import random

# ========== CONFIGURATION ==========
COUNCILS = [
    {
        "name": "Wyndham City Council",
        "logo": "https://www.wyndham.vic.gov.au/themes/custom/wyndham/logo.png",
        "color": "#1565c0"
    },
    {
        "name": "Council Whyndah",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/5/5f/City_of_Whyndah_logo.png",  # You can replace with real logo
        "color": "#139496"
    }
]
GOV_ICON = "https://cdn-icons-png.flaticon.com/512/3209/3209872.png"

# ========== STATE INIT ==========
if 'council_idx' not in st.session_state:
    st.session_state['council_idx'] = 0
if 'obligations' not in st.session_state:
    st.session_state['obligations'] = {}
if 'audit_log' not in st.session_state:
    st.session_state['audit_log'] = []
if 'search_text' not in st.session_state:
    st.session_state['search_text'] = ""
if 'recent_uploads' not in st.session_state:
    st.session_state['recent_uploads'] = []
if 'dark_mode' not in st.session_state:
    st.session_state['dark_mode'] = False
if 'show_onboarding' not in st.session_state:
    st.session_state['show_onboarding'] = True
if 'upload_confetti' not in st.session_state:
    st.session_state['upload_confetti'] = False
if 'feedback' not in st.session_state:
    st.session_state['feedback'] = {}  # {filename: True/False/None}
if 'autosaved' not in st.session_state:
    st.session_state['autosaved'] = True

# ========== UTILITIES ==========
def council():
    return COUNCILS[st.session_state['council_idx']]

# ========== PAGE STYLING ==========
st.set_page_config(page_title="PolicySimplify AI", page_icon="✅", layout="centered")
primary_color = council()["color"] if not st.session_state["dark_mode"] else "#212121"
bg_color = "#eaf3fa" if not st.session_state["dark_mode"] else "#131924"
txt_color = "#1966b2" if not st.session_state["dark_mode"] else "#f4f4f4"
alt_bg = "#fff" if not st.session_state["dark_mode"] else "#1b2537"

st.markdown(f"""
    <style>
    body, .stApp {{ background-color: {bg_color}; }}
    .main {{ background-color: {bg_color}; }}
    .reportview-container {{ background-color: {bg_color}; }}
    .reminder {{ color: #fff; background:#e65c5c; padding: 6px 12px; border-radius: 6px; margin-right: 8px; }}
    .reminder-upcoming {{ color: #fff; background:#f3c852; padding: 6px 12px; border-radius: 6px; margin-right: 8px; }}
    html, body, input, textarea {{ font-size: 18px !important; }}
    </style>
""", unsafe_allow_html=True)

# ========== SIDEBAR ==========
with st.sidebar:
    # Dark mode toggle
    if st.button("🌙" if not st.session_state["dark_mode"] else "☀️", help="Toggle dark mode"):
        st.session_state["dark_mode"] = not st.session_state["dark_mode"]
        st.experimental_rerun()
    st.selectbox("Switch Council", [c["name"] for c in COUNCILS], index=st.session_state['council_idx'],
                 key="council_idx", on_change=lambda: st.experimental_rerun())
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom: 18px;">
            <img src="{council()['logo']}" width="54" style="border-radius:13px;box-shadow:0 1px 8px #1112;" alt="Council Logo"/>
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
    st.caption("🔒 All data stored securely in Australia.")

# ========== HERO HEADER ==========
st.markdown(f"""
<style>
.hero-container {{
    margin: 38px auto 0 auto;
    max-width: 710px;
}}
.hero-card {{
    background: linear-gradient(90deg, {primary_color} 0%, #44bbff 100%);
    color: #fff;
    border-radius: 32px;
    box-shadow: 0 4px 28px #1966b222;
    padding: 32px 44px 26px 44px;
    margin-bottom: 42px;
    text-align: left;
    min-width: 320px;
}}
.hero-row {{
    display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
}}
.hero-title {{
    font-size: 2.45em; font-weight: 900; letter-spacing: -1px; color: #fff; display: flex; align-items: center; gap: 13px;
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
.hero-sub {{ font-size: 1.22em; color: #e3f2fd; font-weight: 400; margin-bottom: 4px; margin-top: 2px; }}
@media (max-width:650px){{.hero-card{{padding:16px 8px 16px 8px;}} .hero-title{{font-size:1.47em;}}}}
</style>
<div class="hero-container">
<div class="hero-card">
    <div class="hero-row">
        <img src="{GOV_ICON}" width="56" height="56" style="border-radius:18px;box-shadow:0 2px 12px #1579c099;object-fit:cover;" class="hero-icon-bounce" alt="Book Icon"/>
        <div>
            <div class="hero-title">
                PolicySimplify AI <span class="hero-ai-flare" title="AI-powered"></span>
            </div>
            <div class="hero-sub"><b>Council:</b> {council()['name']}</div>
            <div style="font-size:1.01em; margin:5px 0 0 0;color:#eafff3;">
                Upload council policies & instantly see what matters.<br>
                <span style="color:#e4ffd7;font-weight:500;">Australian-hosted • Secure • Unlimited uploads</span>
            </div>
        </div>
    </div>
</div>
</div>
""", unsafe_allow_html=True)

# ========== STEP 12: ONBOARDING TOOLTIP ==========
if st.session_state["show_onboarding"]:
    st.info("👋 Welcome! Start by uploading a council policy PDF, then click the ‘?’ icons for help at any time.", icon="👋")
    if st.button("Got it! Hide this tip", key="hide_onboard"):
        st.session_state["show_onboarding"] = False
        st.experimental_rerun()

# ========== UPLOAD CARD (with HELP) ==========
st.markdown(f"""
<div class="upload-card" aria-label="Upload area" style="background:{alt_bg};">
    <div class="upload-icon">📥</div>
    <div class="upload-title">Upload Policy PDF(s)
        <span title="Upload your council policy documents here. Supported: PDF. Max 200MB each." style="cursor:help;font-weight:bold; color:{primary_color}; margin-left:7px;">❓</span>
    </div>
    <div class="upload-sub" style="color:#388e3c;">Drag & drop or click to select policy documents.<br>
    <span style="color:#4caf50;">Max 200MB each • PDF only</span></div>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed"
)

st.markdown("---")

# ========== STEP 14: SHARE BUTTON ==========
st.markdown("""
<div style="margin-bottom:24px;">
    <button onclick="navigator.clipboard.writeText(window.location.href);alert('Page URL copied!')" style="background:#1764a7;color:white;padding:7px 19px;border:none;border-radius:9px;margin-right:10px;cursor:pointer;font-size:1em;">🔗 Share this tool</button>
</div>
""", unsafe_allow_html=True)

# ========== OPENAI KEY ==========
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ========== HELPERS ==========
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
    if not deadline_str: return "#eaf3fa"  # default
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

# ========== MAIN LOGIC ==========
if uploaded_files:
    all_policy_text = ""
    dashboard_data = []
    new_file_uploaded = False
    for uploaded_file in uploaded_files:
        pdf_text = extract_pdf_text(uploaded_file)
        all_policy_text += "\n\n" + pdf_text

        # --- Recent Uploads Logic ---
        uploaded = any(
            entry['filename'] == uploaded_file.name
            for entry in st.session_state['recent_uploads']
        )
        if not uploaded:
            st.session_state['recent_uploads'].insert(0, {
                "filename": uploaded_file.name,
                "uploaded_at": datetime.now().strftime('%Y-%m-%d %H:%M')
            })
            new_file_uploaded = True
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
                st.session_state["autosaved"] = True

    # ========== STEP 13: CONFETTI ON FIRST UPLOAD ==========
    if new_file_uploaded:
        st.balloons()
        st.session_state["upload_confetti"] = True

    # ========== REMINDERS BAR ==========
    st.markdown("### ⏰ Reminders <span title='See all compliance obligations with deadlines.' style='cursor:help;'>❓</span>", unsafe_allow_html=True)
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

    # ========== MOBILE ACTION BAR ==========
    st.markdown("""
    <style>
    @media (max-width:650px){
        .mob-bar{display:flex;position:fixed;bottom:0;left:0;right:0;z-index:99;justify-content:space-evenly;background:#1764a7c0;padding:7px 0;}
        .mob-btn{color:#fff;font-size:1.4em;background:transparent;border:none;cursor:pointer;}
    }
    </style>
    <div class="mob-bar" id="mobile-bar">
      <button class="mob-btn" onclick="window.scrollTo(0,0)" title="Upload">⬆️</button>
      <button class="mob-btn" onclick="document.getElementById('policy_qa').focus()" title="Ask AI">🤖</button>
      <button class="mob-btn" onclick="window.scrollTo(0,document.body.scrollHeight)" title="Audit Log">🕵️</button>
    </div>
    """, unsafe_allow_html=True)

    # ========== FULL-TEXT SEARCH ==========
    st.markdown("---")
    st.markdown("### 🔍 Full-Text Search <span title='Search obligations, summaries, and policies.' style='cursor:help;'>❓</span>", unsafe_allow_html=True)
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

    # ========== STEP 15: AUTOSAVE & TICK ==========
    st.markdown(
        "<span style='font-size:1.1em;color:#59c12a;'>" + ("All changes autosaved ✔️" if st.session_state["autosaved"] else "Saving...") + "</span>",
        unsafe_allow_html=True
    )

    # ========== STEP 16: VISUAL OBLIGATION CARDS ==========
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
                    <span title="Was this summary helpful? Click thumbs up/down." style="cursor:pointer;">
                        👍<input type="radio" name="fb{fname}{idx}" {('checked' if st.session_state['feedback'].get(fname+str(idx))==True else '')} onclick="window.location.reload()"/> 
                        👎<input type="radio" name="fb{fname}{idx}" {('checked' if st.session_state['feedback'].get(fname+str(idx))==False else '')} onclick="window.location.reload()"/>
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

    # ========== STEP 17: POLICY Q&A CHAT ==========
    st.markdown("---")
    st.markdown("## 🤖 Ask Your Policies (AI Chat) <span title='Ask questions about your policies. Answers are only based on your uploaded documents.' style='cursor:help;'>❓</span>", unsafe_allow_html=True)
    query = st.text_input("Ask a policy/compliance question", key="policy_qa")
    if query:
        with st.spinner("Getting answer..."):
            answer = ai_chat(query, all_policy_text)
        st.success(answer)

    # ========== STEP 18: AUDIT LOG ==========
    st.markdown("---")
    st.markdown("## 🕵️ Audit Log <span title='See all actions for compliance.' style='cursor:help;'>❓</span>", unsafe_allow_html=True)
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
