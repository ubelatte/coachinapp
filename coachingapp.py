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

# === GPT PROCESSING ===
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
You are a workplace coaching assistant. Using the data below, generate:
1. Incident Summary
2. Expectations Going Forward
3. Tags
4. Severity

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
You are a leadership coach. Using the data below, generate:
1. Private Coaching Tips
2. Tone Guidance
3. Follow-up Recommendation
4. Supervisor Accountability Tip
5. Three leadership reflection questions

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

        if language.lower() != "english":
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

    # === DOCX GENERATION ===
    def build_coaching_doc():
        doc = Document()
        doc.add_heading("Employee Coaching & Counseling Form", 0)
        doc.add_paragraph(f"(Created {date.today().strftime('%m/%d/%y')})\n")

        doc.add_heading("Section 1 – Supervisor Entry", level=1)
        doc.add_paragraph(f"Date when Incident occurred: {latest['Date of Incident']}")
        doc.add_paragraph(f"Department Name: {latest['Department']}")
        doc.add_paragraph(f"Employee Name: {latest['Employee Name']}")
        doc.add_paragraph(f"Supervisor Name: {latest['Supervisor Name']}")
        doc.add_paragraph(f"Action Taken: {latest['Action Taken']}")
        doc.add_paragraph(f"Issue Type: {latest['Issue Type']}")
        doc.add_paragraph(f"Incident Description: {latest['Incident Description']}")
        doc.add_paragraph(f"Estimated or Actual Cost: {latest['Estimated/Annual Cost'] or '________________________'}")
        doc.add_paragraph(f"Language Spoken: {latest['Language Spoken']}")
        doc.add_paragraph(f"Prior Actions Taken: {latest['Previous Coaching/Warnings']}\n")

        doc.add_heading("Section 2 – AI-Generated Coaching Report", level=1)
        for section in ["Incident Summary", "Expectations Going Forward", "Tags", "Severity"]:
            part = coaching_response.split(f"**{section}:**")
            if len(part) > 1:
                doc.add_paragraph(f"{section}:", style="List Bullet").bold = True
                doc.add_paragraph(part[1].strip())

        doc.add_paragraph("\nAcknowledgment of Receipt:\nI understand that this document serves as a formal record of the counseling provided. I acknowledge that the issue has been discussed with me, and I understand the expectations going forward. My signature below does not necessarily indicate agreement but confirms that I have received and reviewed this documentation.\n")
        doc.add_paragraph("Employee Signature: _________________________        Date: ________________")
        doc.add_paragraph("Supervisor Signature: ________________________        Date: ________________")
        return doc

    def build_leadership_doc():
        doc = Document()
        doc.add_heading("Leadership Reflection", 0)
        for section in ["Private Coaching Tips", "Tone Guidance", "Follow-up Recommendation", "Supervisor Accountability Tip", "Three leadership reflection questions"]:
            part = leadership_response.split(f"**{section}:**")
            if len(part) > 1:
                doc.add_heading(section, level=2)
                doc.add_paragraph(part[1].strip())
            else:
                doc.add_paragraph(leadership_response)
        return doc

    timestamp = int(time.time())
    employee_name_clean = employee.replace(" ", "_")

    coaching_io = BytesIO()
    build_coaching_doc().save(coaching_io)
    coaching_io.seek(0)

    leadership_io = BytesIO()
    build_leadership_doc().save(leadership_io)
    leadership_io.seek(0)

    # === DOWNLOAD BUTTONS ===
    st.success("✅ AI coaching documents are ready!")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 Download Coaching Form",
            data=coaching_io,
            file_name=f"coaching_{employee_name_clean}_{timestamp}.docx"
        )
    with col2:
        st.download_button(
            "📥 Download Leadership Reflection",
            data=leadership_io,
            file_name=f"leadership_{employee_name_clean}_{timestamp}.docx"
        )
