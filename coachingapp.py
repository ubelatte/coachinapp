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

    # Language field with "Other" support
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
You are a leadership coach. Using the data below, generate a private reflection including coaching tips, tone guidance, and 3 reflection questions.

Supervisor: {latest['Supervisor Name']}
Employee: {latest['Employee Name']}
Department: {latest['Department']}
Issue Type: {latest['Issue Type']}
Description: {latest['Incident Description']}
"""

    client_openai = OpenAI(api_key=st.secrets["openai"]["api_key"])

    with st.spinner("🤖 Generating coaching & leadership insights..."):
        # Coaching response
        coaching_response = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful HR assistant."},
                {"role": "user", "content": prompt_coaching},
            ],
            temperature=0.7,
        ).choices[0].message.content.strip()

        # Translate if needed
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

        # Leadership response
        leadership_response = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a leadership coach."},
                {"role": "user", "content": prompt_leadership},
            ],
            temperature=0.7,
        ).choices[0].message.content.strip()

    # === DOCX GENERATION ===
    def build_doc(title, content):
        doc = Document()
        doc.add_heading(title, 0)
        for para in content.strip().split("\n"):
            doc.add_paragraph(para)
        return doc

    timestamp = int(time.time())
    employee_name_clean = employee.replace(" ", "_")

    coaching_io = BytesIO()
    build_doc("Employee Coaching Report", coaching_response).save(coaching_io)
    coaching_io.seek(0)

    leadership_io = BytesIO()
    build_doc("Leadership Reflection", leadership_response).save(leadership_io)
    leadership_io.seek(0)

    # === DOWNLOAD ===
    st.success("✅ AI coaching documents are ready!")
    st.download_button(
        "📥 Download Coaching Document",
        data=coaching_io,
        file_name=f"coaching_{employee_name_clean}_{timestamp}.docx"
    )
    st.download_button(
        "📥 Download Leadership Reflection",
        data=leadership_io,
        file_name=f"leadership_{employee_name_clean}_{timestamp}.docx"
    )
