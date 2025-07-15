import streamlit as st
from openai import OpenAI
from docx import Document
from docx.shared import Pt
from io import BytesIO
from datetime import date
import time

# === PAGE SETTINGS ===
st.set_page_config(page_title="Mestek Coaching Generator", page_icon=None)
st.title("📄 Mestek AI Coaching Generator")

# === PASSWORD PROTECTION ===
PASSWORD = "WFHQmestek413"
if st.text_input("Enter password:", type="password") != PASSWORD:
    st.warning("Please type the correct password and hit Enter.")
    st.stop()

# === STREAMLIT FORM ===
with st.form("coaching_form"):
    supervisor = st.selectbox("Supervisor Name", [
        "Marty", "Nick", "Pete", "Ralph", "Steve", "Bill", "John",
        "Janitza", "Fundi", "Lisa", "Dave", "Dean"
    ])
    employee = st.text_input("Employee Name")
    department = st.selectbox("Department", [
        "Rough In", "Paint Line (NP)", "Commercial Fabrication",
        "Baseboard Accessories", "Maintenance", "Residential Fabrication",
        "Residential Assembly/Packing", "Warehouse (55WIPR)",
        "Convector & Twin Flo", "Shipping/Receiving/Drivers",
        "Dadanco Fabrication/Assembly", "Paint Line (Dadanco)"
    ])
    incident_date = st.date_input("Date of Incident", value=date.today())
    issue_type = st.selectbox("Issue Type", [
        "Attendance", "Safety", "Behavior", "Performance",
        "Policy Violation", "Recognition"
    ])
    action_taken = st.selectbox("Action to be Taken", [
        "Coaching", "Verbal Warning", "Written Warning", "Suspension", "Termination"
    ])
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

def parse_coaching_sections(raw_text):
    sections = {}
    current_section = None
    buffer = []
    for line in raw_text.splitlines():
        line = line.strip()
        if line.endswith(":") and line[:-1] in ["Incident Summary", "Expectations Going Forward", "Tags", "Severity"]:
            if current_section and buffer:
                sections[current_section] = " ".join(buffer).strip()
                buffer = []
            current_section = line[:-1]
        elif current_section:
            buffer.append(line)
    if current_section and buffer:
        sections[current_section] = " ".join(buffer).strip()
    return sections

def build_coaching_doc(latest, coaching_dict):
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

    doc.add_page_break()
    doc.add_heading("Section 2 – AI-Generated Coaching Report", level=1)
    for section in ["Incident Summary", "Expectations Going Forward", "Tags", "Severity"]:
        if section in coaching_dict:
            add_section_header(doc, section + ":")
            doc.add_paragraph(coaching_dict[section])

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

    # Section 1 metadata
    add_bold_para(doc, "Supervisor Name:", latest["Supervisor Name"])
    add_bold_para(doc, "Employee Name:", latest["Employee Name"])
    add_bold_para(doc, "Department:", latest["Department"])
    add_bold_para(doc, "Issue Type:", latest["Issue Type"])
    add_bold_para(doc, "Date of Incident:", latest["Date of Incident"])

    doc.add_page_break()
    doc.add_heading("AI-Generated Leadership Guidance", level=1)

    # Parse leadership_text into sections
    sections = ["Private Reflection", "Coaching Tips", "Tone Guidance", "Follow-Up Recommendation", "Supervisor Accountability Tip"]
    current_title = None
    buffer = []

    lines = leadership_text.splitlines()
    for line in lines + [""]:  # Add empty line to force flush at end
        stripped = line.strip()
        if stripped.endswith(":") and stripped[:-1] in sections:
            if current_title and buffer:
                # Add previous section
                doc.add_paragraph(current_title + ":", style='Heading 3')
                for para in buffer:
                    doc.add_paragraph(para.strip())
                buffer = []
            current_title = stripped[:-1]
        elif current_title:
            buffer.append(stripped)

    if current_title and buffer:
        doc.add_paragraph(current_title + ":", style='Heading 3')
        for para in buffer:
            doc.add_paragraph(para.strip())

    return doc


# === MAIN PROCESSING ===
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
You are a workplace coaching assistant. Using the data below, generate a Workplace Coaching Report with the following sections:
Incident Summary:
Expectations Going Forward:
Tags:
Severity:

Data:
Supervisor: {latest['Supervisor Name']}
Employee: {latest['Employee Name']}
Department: {latest['Department']}
Date of Incident: {latest['Date of Incident']}
Issue Type: {latest['Issue Type']}
Action Taken: {latest['Action Taken']}
Description: {latest['Incident Description']}
"""

    prompt_leadership = f"""
You are a leadership coach. Using the data below, generate a private reflection including coaching tips, tone guidance, follow-up recommendation, and a supervisor accountability tip.

Supervisor: {latest['Supervisor Name']}
Employee: {latest['Employee Name']}
Department: {latest['Department']}
Issue Type: {latest['Issue Type']}
Description: {latest['Incident Description']}
"""

    client_openai = OpenAI(api_key=st.secrets["openai"]["api_key"])
    with st.spinner("🤖 Generating coaching & leadership insights..."):
        coaching_response = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful HR assistant."},
                {"role": "user", "content": prompt_coaching},
            ],
            temperature=0.7,
        ).choices[0].message.content.strip()

        if language.strip().lower() != "english":
            translation_prompt = f"Translate the following into {language.title()} professionally:\n{coaching_response}"
            coaching_response = client_openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You translate workplace HR documents professionally."},
                    {"role": "user", "content": translation_prompt},
                ],
                temperature=0.3,
            ).choices[0].message.content.strip()

        coaching_sections = parse_coaching_sections(coaching_response)

        leadership_response = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a leadership coach."},
                {"role": "user", "content": prompt_leadership},
            ],
            temperature=0.7,
        ).choices[0].message.content.strip()

    timestamp = int(time.time())
    employee_name_clean = employee.replace(" ", "_")

    coaching_io = BytesIO()
    build_coaching_doc(latest, coaching_sections).save(coaching_io)
    coaching_io.seek(0)

    leadership_io = BytesIO()
    build_leadership_doc(latest, leadership_response).save(leadership_io)
    leadership_io.seek(0)

    st.success("✅ Coaching documents ready:")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Download Coaching Document", data=coaching_io,
                           file_name=f"coaching_{employee_name_clean}_{timestamp}.docx")
    with col2:
        st.download_button("Download Leadership Reflection", data=leadership_io,
                           file_name=f"leadership_{employee_name_clean}_{timestamp}.docx")
