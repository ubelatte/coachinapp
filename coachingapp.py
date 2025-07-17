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

# === FORM SETUP ===
st.header("📝 Coaching Report Form")
with st.form("coaching_form"):
    email = st.text_input("Email Address")
    supervisor = st.text_input("Supervisor Name")
    employee = st.text_input("Employee Name")
    department = st.selectbox("Department", [
        "Commercial Fabrication", "Baseboard Accessories", "Maintenance",
        "Residential Fabrication", "Residential Assembly/Packing", "Warehouse (55WIPR)",
        "Convector & Twin Flo", "Shipping/Receiving/Drivers", "Dadanco Fabrication/Assembly",
        "Paint Line (Dadanco)"
    ])
    date_incident = st.date_input("Date of Incident")
    issue_type = st.text_input("Issue Type")
    action_taken = st.text_input("Action to be Taken")
    description = st.text_area("Incident Description")
    cost = st.text_input("Estimated/Annual Cost")
    language = st.selectbox("Language Spoken", ["English", "Spanish", "Other"])
    previous = st.text_area("Previous Coaching/Warnings")
    submitted = st.form_submit_button("Generate Coaching Report")

# === AI + DOCX GENERATION ===
def generate_coaching_doc():
    prompt = f"""
You are an HR analyst helping a supervisor document a coaching session. Based on the following information:

Employee: {employee}
Supervisor: {supervisor}
Department: {department}
Date of Incident: {date_incident}
Issue Type: {issue_type}
Action to be Taken: {action_taken}
Incident Description: {description}
Previous Coaching: {previous}

Generate a 1-paragraph coaching summary and clear expectations moving forward. End with a brief coaching tone reminder.
"""
    try:
        response = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"(AI generation failed: {e})"

def create_doc(content):
    doc = Document()
    doc.add_heading("Employee Coaching Form", level=1).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    section = doc.add_paragraph()
    for label, value in [
        ("Employee Name:", employee),
        ("Supervisor Name:", supervisor),
        ("Department:", department),
        ("Date of Incident:", str(date_incident)),
        ("Issue Type:", issue_type),
        ("Action to be Taken:", action_taken),
        ("Estimated/Annual Cost:", cost),
        ("Language Spoken:", language),
        ("Previous Coaching/Warnings:", previous)
    ]:
        run = section.add_run(f"{label} ")
        run.bold = True
        section.add_run(f"{value}\n")

    doc.add_heading("AI-Generated Coaching Summary", level=2)
    doc.add_paragraph(content)

    doc.add_paragraph("\nAcknowledgment:", style='Heading 2')
    doc.add_paragraph("Employee Signature: _________________________    Date: ____________")
    doc.add_paragraph("Supervisor Signature: _______________________  Date: ____________")

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# === SHEET LOGGING ===
def log_to_sheet():
    row = [
        datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S"), email, supervisor, employee,
        department, str(date_incident), issue_type, action_taken, description,
        cost, language, previous
    ] + ["" for _ in range(12)]  # Empty columns to match existing header spacing
    sheet.append_row(row, value_input_option="USER_ENTERED")

# === FORM SUBMISSION ===
if submitted:
    if not all([employee, supervisor, description]):
        st.error("Please complete all required fields.")
    else:
        summary = generate_coaching_doc()
        file = create_doc(summary)
        log_to_sheet()

        st.success("✅ Coaching report generated and saved!")
        st.download_button(
            label="📄 Download Coaching Report",
            data=file,
            file_name=f"{employee}_Coaching_Report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
