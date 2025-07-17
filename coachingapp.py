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

# === DOCX GENERATION ===
def generate_docx(supervisor, employee, department, date, description, expectations):
    doc = Document()
    doc.add_heading("Coaching Report", 0).alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

    fields = [
        ("Supervisor Name:", supervisor),
        ("Employee Name:", employee),
        ("Department:", department),
        ("Date of Incident:", date),
        ("Incident Description:", description),
        ("Expectations Going Forward:", expectations)
    ]
    for label, value in fields:
        para = doc.add_paragraph()
        para.add_run(label + " ").bold = True
        para.add_run(value)

    doc.add_paragraph("\nSignatures:")
    doc.add_paragraph("Employee Signature: ______________________    Date: __________")
    doc.add_paragraph("Supervisor Signature: _____________________    Date: __________")

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# === FORM ===
if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False

with st.form("coaching_form"):
    email = st.text_input("Supervisor Email")
    supervisor = st.text_input("Supervisor Name")
    employee = st.text_input("Employee Name")
    department = st.selectbox("Department", [
        "Rough In", "Paint Line (NP)", "Commercial Fabrication",
        "Baseboard Accessories", "Maintenance", "Residential Fabrication",
        "Residential Assembly/Packing", "Warehouse (55WIPR)",
        "Convector & Twin Flo", "Shipping/Receiving/Drivers",
        "Dadanco Fabrication/Assembly", "Paint Line (Dadanco)"
    ])
    date = st.date_input("Date of Incident", value=datetime.date.today())
    issue = st.text_input("Issue Type")
    action = st.text_input("Action to be Taken")
    description = st.text_area("Incident Description")
    cost = st.text_input("Estimated/Annual Cost")
    language = st.selectbox("Language Spoken", ["English", "Spanish", "Other"])
    previous = st.text_area("Previous Coaching/Warnings")

    expectations = st.text_area("Expectations Going Forward")

    submitted = st.form_submit_button("Generate Coaching Report")

    if submitted:
        if not all([supervisor, employee, department, description, expectations]):
            st.warning("Please complete all required fields.")
        else:
            timestamp = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            row = [
                timestamp, email, supervisor, employee, department,
                str(date), issue, action, description, cost, language, previous
            ] + [""] * 12  # Padding to align with full sheet structure if needed
            sheet.append_row(row, value_input_option="USER_ENTERED")
            st.success("✅ Logged to sheet")

            st.session_state.report_docx = generate_docx(
                supervisor, employee, department, str(date), description, expectations
            )
            st.session_state.form_submitted = True

# === REPORT DOWNLOAD ===
if st.session_state.get("form_submitted") and "report_docx" in st.session_state:
    st.download_button(
        label="📄 Download Coaching Report",
        data=st.session_state.report_docx,
        file_name=f"{st.session_state.get('employee', 'coaching')}_report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
