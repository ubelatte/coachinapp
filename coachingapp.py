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
import re

# === PASSWORD GATE ===
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

st.success("Access granted!")

# === GOOGLE + OPENAI SETUP ===
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)

try:
    sheet = client.open("Coaching Assessment Form").sheet1
    st.success("✅ Connected to Google Sheet")
except Exception as e:
    st.error(f"❌ Sheet error: {e}")

client_openai = OpenAI(api_key=st.secrets["openai"]["api_key"])

# === AI FUNCTIONS ===
def analyze_text(text):
    prompt = f"Generate a coaching summary from this incident: {text}\nInclude expectations going forward."
    try:
        completion = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"(AI Error: {e})"

# === DOCX GENERATION ===
def create_doc(employee, supervisor, department, date, issue_type, action, description, cost, language, previous):
    summary = analyze_text(description)
    doc = Document()
    doc.add_heading("Coaching Report", level=1).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    fields = [
        ("Employee Name:", employee),
        ("Supervisor Name:", supervisor),
        ("Department:", department),
        ("Date of Incident:", date),
        ("Issue Type:", issue_type),
        ("Action to be Taken:", action),
        ("Estimated/Annual Cost:", cost),
        ("Language Spoken:", language),
        ("Previous Coaching/Warnings:", previous),
    ]
    for label, value in fields:
        p = doc.add_paragraph()
        r1 = p.add_run(label + " ")
        r1.bold = True
        p.add_run(value)

    doc.add_paragraph("\nIncident Description", style='Heading 2')
    doc.add_paragraph(description)

    doc.add_paragraph("\nAI-Generated Coaching Summary", style='Heading 2')
    doc.add_paragraph(summary)

    doc.add_paragraph("\nSign-Offs", style='Heading 2')
    doc.add_paragraph("Employee Signature: ________________________________    Date: ____________")
    doc.add_paragraph("Supervisor Signature: ________________________________  Date: ____________")

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer, summary

# === UI FORM ===
if 'submitted' not in st.session_state:
    st.session_state.submitted = False

with st.form("coaching_form"):
    email = st.text_input("Email Address")
    supervisor = st.text_input("Supervisor Name")
    employee = st.text_input("Employee Name")
    department = st.text_input("Department")
    date = st.date_input("Date of Incident", value=datetime.date.today())
    issue_type = st.selectbox("Issue Type", ["Performance", "Behavior", "Attendance", "Other"])
    action = st.selectbox("Action to be Taken", ["Coaching", "Verbal Warning", "Written Warning", "Final Warning"])
    description = st.text_area("Incident Description")
    cost = st.text_input("Estimated/Annual Cost")
    language = st.selectbox("Language Spoken", ["English", "Spanish", "Other"])
    previous = st.text_area("Previous Coaching/Warnings")
    submitted = st.form_submit_button("Generate Coaching Report")

    if submitted and all([email, supervisor, employee, department, description]):
        st.session_state.submitted = True
        st.session_state.data = {
            "email": email,
            "supervisor": supervisor,
            "employee": employee,
            "department": department,
            "date": str(date),
            "issue_type": issue_type,
            "action": action,
            "description": description,
            "cost": cost,
            "language": language,
            "previous": previous
        }

# === LOGGING + DOWNLOAD ===
if st.session_state.submitted:
    data = st.session_state.data
    docx_file, ai_summary = create_doc(
        data["employee"], data["supervisor"], data["department"], data["date"],
        data["issue_type"], data["action"], data["description"],
        data["cost"], data["language"], data["previous"]
    )

    timestamp = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    row = [
        timestamp, data["email"], data["supervisor"], data["employee"],
        data["department"], data["date"], data["issue_type"],
        data["action"], data["description"], data["cost"],
        data["language"], data["previous"]
    ]
    try:
        sheet.append_row(row, value_input_option="USER_ENTERED")
        st.success("✅ Entry logged to Google Sheet")
    except Exception as e:
        st.error(f"❌ Failed to log entry: {e}")

    st.download_button(
        label="📄 Download Coaching Report",
        data=docx_file,
        file_name=f"{data['employee'].replace(' ', '_')}_Coaching_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    st.session_state.submitted = False
