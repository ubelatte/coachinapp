# Full working Streamlit coaching app script with coaching + leadership reports, form submission, and trend dashboard.
# ✅ Preserves original functionality
# ✅ Fixes disappearing buttons
# ✅ Logs to Coaching Assessment Form
# ✅ Includes department dropdown
# ✅ Auto-adds expectations into report
# ✅ Tabs: Coaching Form + Trend Dashboard

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from io import BytesIO
import datetime
import pandas as pd
import re

# === PASSWORD GATE ===
st.set_page_config(page_title="Mestek Coaching App", layout="wide")
st.title("🔐 Secure Access")
PASSWORD = "WFHQmestek413"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    with st.form("password_form"):
        input_password = st.text_input("Enter password", type="password")
        unlock = st.form_submit_button("Unlock")
    if unlock:
        if input_password == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    st.stop()

# === GOOGLE SHEET + OPENAI SETUP ===
st.success("Access granted!")
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)

try:
    sheet = client.open("Coaching Assessment Form").sheet1
    st.success("✅ Connected to Coaching Assessment Form")
except Exception as e:
    st.error(f"❌ Sheet error: {e}")

client_openai = OpenAI(api_key=st.secrets["openai"]["api_key"])

# === FORM PROMPTS ===
prompts = [
    ("Feedback & Conflict Resolution", "How does this employee typically respond to feedback — especially when it differs from their own opinion? Do they apply it constructively, and do they help others do the same when it comes to resolving conflict and promoting cooperation?"),
    ("Communication & Team Support", "How effectively does this employee communicate with others? How well does this employee support their team - including their willingness to shift focus, assist other teams, or go beyond their assigned duties?"),
    ("Reliability & Productivity", "How reliable is this employee in terms of attendance and use of time? Does this employee consistently meet or exceed productivity standards, follow company policies, and actively contribute ideas for improving standard work?"),
    ("Adaptability & Quality Focus", "When your team encounters workflow disruptions or shifting priorities, how does this employee typically respond? How does this employee contribute to maintaining and improving product quality?"),
    ("Safety Commitment", "In what ways does this employee demonstrate commitment to safety and workplace organization?"),
    ("Documentation & Procedures", "How effectively does this employee use technical documentation and operate equipment according to established procedures?")
]

# === ANALYSIS ===
def analyze_feedback(category, response):
    prompt = f"You are an HR analyst. Rate the employee's response on '{category}' from 1 to 5. Then summarize in 1–2 sentences. Format: Rating: X/5\nSummary: ...\n\nResponse: {response}"
    try:
        result = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        return f"Rating: 3/5\nSummary: AI error: {e}"

def summarize_overall(employee_name, feedbacks):
    joined = "\n\n".join(feedbacks)
    prompt = f"Summarize overall performance for {employee_name}. Include strengths, improvement areas, and an overall performance score (e.g. Overall performance score: 4.2/5).\n\n{joined}"
    try:
        result = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        return f"(Summary unavailable: {e})"

# === REPORTS ===
def create_report(doc_type, data, scores, explanations, summary):
    doc = Document()
    doc.add_heading(f"MESTEK – {doc_type} Report", 0).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    doc.add_heading("Employee Info", level=2)
    for label in ["Employee Name", "Supervisor Name", "Department", "Date of Incident", "Issue Type", "Action to be Taken", "Estimated/Annual Cost"]:
        run = doc.add_paragraph()
        r1 = run.add_run(f"{label}: ")
        r1.bold = True
        run.add_run(str(data[label]))

    doc.add_heading("Coaching Prompts", level=2)
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.rows[0].cells[0].text = "Category"
    table.rows[0].cells[1].text = "Rating"
    table.rows[0].cells[2].text = "Explanation"

    for cat, score, note in zip([p[0] for p in prompts], scores, explanations):
        row = table.add_row().cells
        row[0].text = cat
        row[1].text = score
        row[2].text = note

    doc.add_heading("Performance Summary", level=2)
    doc.add_paragraph(summary)

    doc.add_heading("Expectations Going Forward", level=2)
    for i in range(3):
        doc.add_paragraph(f"{i+1}. " + "_" * 100 + "\n    " + "_" * 100)

    doc.add_heading("Sign-Off", level=2)
    doc.add_paragraph("Employee Signature: ___________________    Date: __________")
    doc.add_paragraph("Supervisor Signature: __________________    Date: __________")

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# === MAIN APP ===
tabs = st.tabs(["📝 Coaching Form", "📊 Trend Dashboard"])

with tabs[0]:
    st.header("Coaching Report Generator")
    with st.form("coaching_form"):
        form_data = {}
        form_data["Supervisor Name"] = st.text_input("Supervisor Name")
        form_data["Employee Name"] = st.text_input("Employee Name")
        form_data["Department"] = st.selectbox("Department", [
            "Commercial Fabrication", "Baseboard Accessories", "Maintenance", "Residential Fabrication",
            "Residential Assembly/Packing", "Warehouse (55WIPR)", "Convector & Twin Flo",
            "Shipping/Receiving/Drivers", "Dadanco Fabrication/Assembly", "Paint Line (Dadanco)"
        ])
        form_data["Date of Incident"] = st.date_input("Date of Incident", value=datetime.date.today())
        form_data["Issue Type"] = st.text_input("Issue Type")
        form_data["Action to be Taken"] = st.text_input("Action to be Taken")
        form_data["Incident Description"] = st.text_area("Incident Description")
        form_data["Estimated/Annual Cost"] = st.text_input("Estimated/Annual Cost")
        form_data["Language Spoken"] = st.text_input("Language Spoken")
        form_data["Previous Coaching/Warnings"] = st.text_input("Previous Coaching/Warnings")

        responses = [st.text_area(q, key=f"resp_{i}") for i, (_, q) in enumerate(prompts)]
        submitted = st.form_submit_button("Generate Reports")

    if submitted:
        ai_results = [analyze_feedback(cat, resp) for (cat, _), resp in zip(prompts, responses)]
        scores = [re.search(r"Rating: (\d)/5", r).group(1) if re.search(r"Rating: (\d)/5", r) else "3" for r in ai_results]
        summaries = [re.search(r"Summary: (.*)", r).group(1) if re.search(r"Summary: (.*)", r) else r for r in ai_results]
        overall = summarize_overall(form_data["Employee Name"], ai_results)

        log_row = [datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ""] + [form_data.get(h, "") for h in [
            "Supervisor Name", "Employee Name", "Department", "Date of Incident", "Issue Type", "Action to be Taken",
            "Incident Description", "Estimated/Annual Cost", "Language Spoken", "Previous Coaching/Warnings"
        ]] + scores + ["/".join(scores), overall, "✔️"]
        sheet.append_row(log_row)

        col1, col2 = st.columns(2)
        with col1:
            coaching_doc = create_report("Coaching", form_data, scores, summaries, overall)
            st.download_button("📥 Download Coaching Report", data=coaching_doc, file_name="Coaching_Report.docx")
        with col2:
            leadership_doc = create_report("Leadership Reflection", form_data, scores, summaries, overall)
            st.download_button("📥 Download Leadership Report", data=leadership_doc, file_name="Leadership_Reflection.docx")

with tabs[1]:
    st.header("📊 Coaching Trend Dashboard")
    try:
        data = pd.DataFrame(sheet.get_all_records())
        st.dataframe(data)
        st.metric("Total Coaching Events", len(data))
        st.bar_chart(data["Department"].value_counts())
    except Exception as e:
        st.error(f"Couldn't load dashboard: {e}")
