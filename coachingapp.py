import streamlit as st
from openai import OpenAI
from docx import Document
from io import BytesIO
from datetime import date
import time

# === PAGE SETTINGS ===
st.set_page_config(page_title="Mestek Coaching Generator", page_icon="📄")
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
    if language_option == "Other":
        language = st.text_input("Please specify the language:")
    else:
        language = language_option
    previous = st.radio("Previous Coaching/Warnings", ["Yes", "No"])
    submitted = st.form_submit_button("Generate Coaching Report")

# === GPT + DOC GENERATION ===
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
You are a workplace coaching assistant. Using the data below, generate a coaching report including:
- Incident Summary
- Expectations Going Forward
- Tags
- Severity
- Private Coaching Tips
- Conversation Tone Guidance
- Follow-Up Recommendation
- Supervisor Accountability Tip

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
You are a leadership coach. Using the data below, generate a private reflection including:
- Coaching Tips
- Tone Guidance
- 3 Reflection Questions
- Follow-Up Recommendation
- Supervisor Accountability Tip

Supervisor: {latest['Supervisor Name']}
Employee: {latest['Employee Name']}
Department: {latest['Department']}
Issue Type: {latest['Issue Type']}
Description: {latest['Incident Description']}
"""

    client_openai = OpenAI(api_key=st.secrets["openai"]["api_key"])

    with st.spinner("🤖 Generating documents with AI..."):
        coaching_response = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful HR assistant."},
                {"role": "user", "content": prompt_coaching},
            ],
            temperature=0.7,
        ).choices[0].message.content.strip()

        if language.lower().strip() != "english":
            translation_prompt = f"Translate the following into {language.title()} professionally:\n{coaching_response}"
            coaching_response = client_openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You translate workplace HR documents professionally."},
                    {"role": "user", "content": translation_prompt},
                ],
                temperature=0.3,
            ).choices[0].message.content.strip()

        leadership_response = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a leadership coach."},
                {"role": "user", "content": prompt_leadership},
            ],
            temperature=0.7,
        ).choices[0].message.content.strip()

    # === BUILD COACHING DOC ===
    def build_coaching_doc(data, coaching):
        doc = Document()
        doc.add_heading("Employee Coaching & Counseling Form", 0)
        doc.add_paragraph(f"(Created {date.today().strftime('%m/%d/%y')})")
        doc.add_paragraph("\nSection 1 – Supervisor Entry")
        fields = [
            ("Date when Incident occurred", data['Date of Incident']),
            ("Department Name", data['Department']),
            ("Employee Name", data['Employee Name']),
            ("Supervisor Name", data['Supervisor Name']),
            ("Action Taken", data['Action Taken']),
            ("Issue Type", data['Issue Type']),
            ("Incident Description", data['Incident Description']),
            ("Estimated or Actual Cost", data['Estimated/Annual Cost'] or "________________________"),
            ("Language Spoken", data['Language Spoken']),
            ("Prior Actions Taken", data['Previous Coaching/Warnings']),
        ]
        for label, value in fields:
            p = doc.add_paragraph()
            p.add_run(f"{label}: ").bold = True
            p.add_run(str(value))

        doc.add_paragraph("\nSection 2 – AI-Generated Coaching Report")
        for line in coaching.split("\n"):
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                parts = line.split(":", 1)
                run = doc.add_paragraph()
                run.add_run(parts[0].strip() + ":").bold = True
                run.add_run(" " + parts[1].strip())
            else:
                doc.add_paragraph(line)

        doc.add_paragraph("\nAcknowledgment of Receipt:")
        doc.add_paragraph(
            "I understand that this document serves as a formal record of the counseling provided. "
            "I acknowledge that the issue has been discussed with me, and I understand the expectations going forward. "
            "My signature below does not necessarily indicate agreement but confirms that I have received and reviewed this documentation."
        )
        doc.add_paragraph("\nEmployee Signature: _________________________        Date: ________________")
        doc.add_paragraph("Supervisor Signature: ________________________        Date: ________________")
        return doc

    # === BUILD LEADERSHIP DOC ===
    def build_leadership_doc(content):
        doc = Document()
        doc.add_heading("Private Leadership Reflection", 0)
        for para in content.strip().split("\n"):
            doc.add_paragraph(para)
        return doc

    # === SAVE FILES TO MEMORY ===
    timestamp = int(time.time())
    employee_clean = latest['Employee Name'].replace(" ", "_")

    coaching_io = BytesIO()
    build_coaching_doc(latest, coaching_response).save(coaching_io)
    coaching_io.seek(0)

    leadership_io = BytesIO()
    build_leadership_doc(leadership_response).save(leadership_io)
    leadership_io.seek(0)

    # === DOWNLOAD BUTTONS ===
    st.success("✅ AI-generated documents are ready!")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📄 Download Coaching Report", data=coaching_io, file_name=f"coaching_{employee_clean}_{timestamp}.docx")
    with col2:
        st.download_button("🧠 Download Leadership Reflection", data=leadership_io, file_name=f"leadership_{employee_clean}_{timestamp}.docx")
