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

    prior_actions = st.text_input("Prior Actions Taken (e.g. N/A, Verbal Warning)")

    previous = st.radio("Previous Coaching/Warnings", ["Yes", "No"])

    submitted = st.form_submit_button("Generate Coaching Report")

# === GPT + DOCX HANDLING ===
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
        "Prior Actions Taken": prior_actions,
    }

    prompt = f"""
You are a workplace coaching assistant. Using the data below, generate:

1. Incident Summary
2. Expectations Going Forward
3. Private Coaching Tips
4. Conversation Tone Guidance
5. Tags
6. Severity
7. Follow-Up Recommendation
8. Supervisor Accountability Tip

Data:
Supervisor: {supervisor}
Employee: {employee}
Department: {department}
Date of Incident: {latest['Date of Incident']}
Issue Type: {issue_type}
Action Taken: {action_taken}
Description: {description}
"""

    leadership_prompt = f"""
You are a leadership coach. Using the data below, generate a private reflection including coaching tips, tone guidance, and 3 reflection questions.

Supervisor: {supervisor}
Employee: {employee}
Department: {department}
Issue Type: {issue_type}
Description: {description}
"""

    client_openai = OpenAI(api_key=st.secrets["openai"]["api_key"])

    with st.spinner("🤖 Generating AI coaching & leadership documents..."):
        coaching_text = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful HR assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        ).choices[0].message.content.strip()

        if language.strip().lower() != "english":
            translation_prompt = f"Translate the following into {language.title()} professionally:\n{coaching_text}"
            coaching_text = client_openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You translate workplace HR documents professionally."},
                    {"role": "user", "content": translation_prompt}
                ],
                temperature=0.3,
            ).choices[0].message.content.strip()

        leadership_text = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a leadership coach."},
                {"role": "user", "content": leadership_prompt}
            ],
            temperature=0.7,
        ).choices[0].message.content.strip()

    # === Build Formatted Coaching DOCX ===
    def build_coaching_doc():
        doc = Document()
        doc.add_heading("Employee Coaching & Counseling Form", 0)
        doc.add_paragraph(f"(Created {date.today().strftime('%m/%d/%y')})")

        doc.add_heading("Section 1 – Supervisor Entry", level=1)
        doc.add_paragraph(f"Date when Incident occurred: {latest['Date of Incident']}")
        doc.add_paragraph(f"Department Name: {department}")
        doc.add_paragraph(f"Employee Name: {employee}")
        doc.add_paragraph(f"Supervisor Name: {supervisor}")
        doc.add_paragraph(f"Action Taken: {action_taken}")
        doc.add_paragraph(f"Issue Type: {issue_type}")
        doc.add_paragraph(f"Incident Description: {description}")
        doc.add_paragraph(f"Estimated or Actual Cost: {estimated_cost or '________________________'}")
        doc.add_paragraph(f"Language Spoken: {language}")
        doc.add_paragraph(f"Prior Actions Taken: {prior_actions or 'N/A'}")

        doc.add_heading("Section 2 – AI-Generated Coaching Report", level=1)
        for para in coaching_text.split("\n"):
            doc.add_paragraph(para.strip())

        doc.add_paragraph("\nAcknowledgment of Receipt:")
        doc.add_paragraph(
            "I understand that this document serves as a formal record of the counseling provided. "
            "I acknowledge that the issue has been discussed with me, and I understand the expectations going forward. "
            "My signature below does not necessarily indicate agreement but confirms that I have received and reviewed this documentation."
        )

        doc.add_paragraph("\nEmployee Signature: _________________________        Date: ________________")
        doc.add_paragraph("Supervisor Signature: ________________________        Date: ________________")

        return doc

    def build_leadership_doc():
        doc = Document()
        doc.add_heading("Leadership Reflection", 0)
        for para in leadership_text.split("\n"):
            doc.add_paragraph(para.strip())
        return doc

    # === Write Files to Memory
    timestamp = int(time.time())
    safe_name = employee.replace(" ", "_")

    coaching_doc = BytesIO()
    build_coaching_doc().save(coaching_doc)
    coaching_doc.seek(0)

    leadership_doc = BytesIO()
    build_leadership_doc().save(leadership_doc)
    leadership_doc.seek(0)

    # === Store in session so downloads won't reset form
    st.session_state["coaching_doc"] = coaching_doc
    st.session_state["leadership_doc"] = leadership_doc
    st.session_state["employee_name"] = safe_name
    st.session_state["timestamp"] = timestamp

# === SHOW DOWNLOAD BUTTONS
if "coaching_doc" in st.session_state and "leadership_doc" in st.session_state:
    st.success("✅ AI coaching documents are ready!")

    st.download_button(
        "📥 Download Coaching Document",
        data=st.session_state["coaching_doc"],
        file_name=f"coaching_{st.session_state['employee_name']}_{st.session_state['timestamp']}.docx"
    )
    st.download_button(
        "📥 Download Leadership Reflection",
        data=st.session_state["leadership_doc"],
        file_name=f"leadership_{st.session_state['employee_name']}_{st.session_state['timestamp']}.docx"
    )
