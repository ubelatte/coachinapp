import streamlit as st
from openai import OpenAI
from docx import Document
from docx.shared import Pt
from io import BytesIO
from datetime import date
import time
import re

# === PAGE SETTINGS ===
st.set_page_config(page_title="Mestek Coaching Generator", page_icon="📄")
st.title("📄 Mestek AI Coaching Generator")

# === PASSWORD PROTECTION ===
PASSWORD = "WFHQmestek413"
if st.text_input("Enter password:", type="password") != PASSWORD:
    st.warning("Please type the correct password and hit Enter.")
    st.stop()

# === FORM ===
with st.form("coaching_form"):
    supervisor = st.selectbox("Supervisor Name", [
        "Marty", "Nick", "Pete", "Ralph", "Steve", "Bill", "John",
        "Janitza", "Fundi", "Lisa", "Dave", "Dean"])
    employee = st.text_input("Employee Name")
    department = st.selectbox("Department", [
        "Rough In", "Paint Line (NP)", "Commercial Fabrication",
        "Baseboard Accessories", "Maintenance", "Residential Fabrication",
        "Residential Assembly/Packing", "Warehouse (55WIPR)",
        "Convector & Twin Flo", "Shipping/Receiving/Drivers",
        "Dadanco Fabrication/Assembly", "Paint Line (Dadanco)"])
    incident_date = st.date_input("Date of Incident", value=date.today())
    issue_type = st.selectbox("Issue Type", [
        "Attendance", "Safety", "Behavior", "Performance",
        "Policy Violation", "Recognition"])
    action_taken = st.selectbox("Action to be Taken", [
        "Coaching", "Verbal Warning", "Written Warning", "Suspension", "Termination"])
    description = st.text_area("Incident Description")
    estimated_cost = st.text_input("Estimated/Annual Cost (optional)")
    language_option = st.selectbox("Language Spoken", ["English", "Spanish", "Other"])
    language = st.text_input("Please specify the language:") if language_option == "Other" else language_option
    previous = st.radio("Previous Coaching/Warnings", ["Yes", "No"])
    submitted = st.form_submit_button("Generate Coaching Report")

# === DOCX HELPERS ===
def add_bold_para(doc, label, value):
    para = doc.add_paragraph()
    run = para.add_run(label)
    run.bold = True
    para.add_run(f" {value}")

def add_section_header(doc, text):
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold = True
    run.font.size = Pt(12)

def clean_markdown(text):
    return re.sub(r"\*\*(.*?)\*\*", r"\1", text).replace("**", "").strip()

def extract_section(text, section_name):
    pattern = rf"{section_name}:\s*(.*?)(?=\n\w+?:|$)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return clean_markdown(match.group(1).strip())
    return ""

def build_coaching_doc(latest, full_text):
    doc = Document()
    doc.add_heading("Employee Coaching & Counseling Form", 0)
    doc.add_paragraph(f"(Created {date.today().strftime('%m/%d/%y')})")

    doc.add_heading("Section 1 – Supervisor Entry", level=1)
    add_bold_para(doc, "Date when Incident occurred:", latest["Date of Incident"])
    add_bold_para(doc, "Department Name:", latest["Department"])
    add_bold_para(doc, "Employee Name:", latest["Employee Name"])
    add_bold_para(doc, "Supervisor Name:", latest["Supervisor Name"])
    add_bold_para(doc, "Action Taken:", latest["Action Taken"])
    add_bold_para(doc, "Issue Type:", latest["Issue Type"])
    add_bold_para(doc, "Incident Description:", latest["Incident Description"])
    add_bold_para(doc, "Estimated or Actual Cost:", latest["Estimated/Annual Cost"] or "N/A")
    add_bold_para(doc, "Language Spoken:", latest["Language Spoken"])
    add_bold_para(doc, "Prior Actions Taken:", latest["Previous Coaching/Warnings"])

    doc.add_heading("Section 2 – AI-Generated Coaching Report", level=1)
    for section in ["Incident Summary", "Expectations Going Forward", "Tags", "Severity"]:
        content = extract_section(full_text, section)
        if content:
            add_section_header(doc, f"{section}:")
            doc.add_paragraph(content)

    doc.add_paragraph("\nAcknowledgment of Receipt:")
    doc.add_paragraph(
        "I understand that this document serves as a formal record of the counseling provided. "
        "I acknowledge that the issue has been discussed with me, and I understand the expectations going forward. "
        "My signature below does not necessarily indicate agreement but confirms that I have received and reviewed this documentation."
    )
    doc.add_paragraph("Employee Signature: _________________________        Date: ________________")
    doc.add_paragraph("Supervisor Signature: ________________________        Date: ________________")
    return doc

def build_leadership_doc(latest, leadership_text):
    doc = Document()
    doc.add_heading("Leadership Reflection", 0)
    add_bold_para(doc, "Supervisor Name:", latest["Supervisor Name"])
    add_bold_para(doc, "Employee Name:", latest["Employee Name"])
    add_bold_para(doc, "Department:", latest["Department"])
    add_bold_para(doc, "Issue Type:", latest["Issue Type"])
    add_bold_para(doc, "Date of Incident:", latest["Date of Incident"])
    add_section_header(doc, "\nAI-Generated Leadership Guidance:")
    for para in leadership_text.split("\n"):
        doc.add_paragraph(clean_markdown(para.strip()))
    return doc

# === MAIN LOGIC ===
if submitted:
    latest = {
        "Supervisor Name": supervisor,
        "Employee Name": employee,
        "Department": department,
        "Date of Incident": incident_date.strftime("%Y-%m-%d"),
        "Issue Type": issue_type,
        "Action Taken": action_taken,
        "Incident Description": description,
        "Estimated/Annual Cost": estimated_cost,
        "Language Spoken": language,
        "Previous Coaching/Warnings": previous,
    }

    prompt_coaching = f"""
You are a workplace coaching assistant. Using the data below, generate a coaching report with:
Incident Summary:
Expectations Going Forward:
Tags:
Severity:

Supervisor: {supervisor}
Employee: {employee}
Department: {department}
Date of Incident: {incident_date}
Issue Type: {issue_type}
Action Taken: {action_taken}
Description: {description}
"""

    prompt_leadership = f"""
You are a leadership coach. Using the data below, generate a private reflection including coaching tips, tone guidance, follow-up recommendation, and a supervisor accountability tip.

Supervisor: {supervisor}
Employee: {employee}
Department: {department}
Issue Type: {issue_type}
Description: {description}
"""

    client_openai = OpenAI(api_key=st.secrets["openai"]["api_key"])
    with st.spinner("🤖 Generating coaching & leadership insights..."):
        coaching_full = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful HR assistant."},
                {"role": "user", "content": prompt_coaching},
            ],
            temperature=0.7,
        ).choices[0].message.content.strip()

        if language.strip().lower() != "english":
            translation_prompt = f"Translate this professionally to {language.title()}:\n{coaching_full}"
            coaching_full = client_openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You translate workplace HR documents professionally."},
                    {"role": "user", "content": translation_prompt},
                ],
                temperature=0.3,
            ).choices[0].message.content.strip()

        leadership_text = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a leadership coach."},
                {"role": "user", "content": prompt_leadership},
            ],
            temperature=0.7,
        ).choices[0].message.content.strip()

    # === Generate Files ===
    timestamp = int(time.time())
    filename_base = employee.replace(" ", "_")
    coaching_io = BytesIO()
    build_coaching_doc(latest, coaching_full).save(coaching_io)
    coaching_io.seek(0)
    leadership_io = BytesIO()
    build_leadership_doc(latest, leadership_text).save(leadership_io)
    leadership_io.seek(0)

    # === Download Buttons (Independent) ===
    st.success("✅ Coaching documents ready!")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📄 Download Coaching Document", data=coaching_io,
                           file_name=f"coaching_{filename_base}_{timestamp}.docx")
    with col2:
        st.download_button("📄 Download Leadership Reflection", data=leadership_io,
                           file_name=f"leadership_{filename_base}_{timestamp}.docx")
