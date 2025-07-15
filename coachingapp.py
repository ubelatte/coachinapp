import streamlit as st
import os
import time
import gspread
from google.oauth2.service_account import Credentials
from openai import OpenAI
from docx import Document
from io import BytesIO
import re

# === PAGE SETTINGS ===
st.set_page_config(page_title="Mestek Coaching Generator", page_icon="📄")
st.title("📄 Mestek AI Coaching Generator")

# === PASSWORD PROTECTION ===
PASSWORD = "WFHQmestek413"
if st.text_input("Enter password:", type="password") != PASSWORD:
    st.warning("Access denied.")
    st.stop()

# === CONFIGURATION ===
SHEET_NAME = "Coaching Assessment Form"
OUTPUT_FOLDER = "/tmp"
LEADERSHIP_OUTPUT_FOLDER = "/tmp"

# === AUTH WITH GOOGLE SHEETS ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# === GET LATEST FORM ENTRY ===
data = sheet.get_all_values()
headers = data[0]
rows = data[1:]
latest_row = rows[-1]
latest = dict(zip(headers, latest_row))

# === LANGUAGE DETECTION ===
language = latest.get("Language Spoken", "English").strip().lower()

# === GPT PROMPTS ===
prompt_coaching = f"""
You are a workplace coaching assistant. Using the data below, generate:
1. Incident Summary
2. Expectations Going Forward
3. Tags
4. Severity

Data:
Supervisor: {latest.get('Supervisor Name', '')}
Employee: {latest.get('Employee Name', '')}
Department: {latest.get('Department', '')}
Date of Incident: {latest.get('Date of Incident', '')}
Issue Type: {latest.get('Issue Type', '')}
Action Taken: {latest.get('Action Taken', '')}
Description: {latest.get('Incident Description', '')}
"""

prompt_leadership = f"""
You are a leadership coach. Using the data below, generate a private reflection including coaching tips, tone guidance, and 3 reflection questions.

Supervisor: {latest.get('Supervisor Name', '')}
Employee: {latest.get('Employee Name', '')}
Department: {latest.get('Department', '')}
Issue Type: {latest.get('Issue Type', '')}
Description: {latest.get('Incident Description', '')}
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

    # Translate if needed
    if language != "english":
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

# === BUILD DOCUMENTS ===
def build_doc(title, content):
    doc = Document()
    doc.add_heading(title, 0)
    for para in content.split("\n"):
        doc.add_paragraph(para)
    return doc

os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(LEADERSHIP_OUTPUT_FOLDER, exist_ok=True)

timestamp = int(time.time())
employee_name = latest.get("Employee Name", "unknown").replace(" ", "_")
coaching_filename = f"coaching_{employee_name}_{timestamp}.docx"
leadership_filename = f"leadership_{employee_name}_reflection_{timestamp}.docx"

coaching_doc = build_doc("Employee Coaching Report", coaching_response)
leadership_doc = build_doc("Leadership Reflection", leadership_response)

coaching_io = BytesIO()
leadership_io = BytesIO()
coaching_doc.save(coaching_io)
leadership_doc.save(leadership_io)

# === STREAMLIT DOWNLOAD ===
st.success("✅ AI coaching documents are ready!")
st.download_button("📥 Download Coaching Document", data=coaching_io.getvalue(), file_name=coaching_filename)
st.download_button("📥 Download Leadership Reflection", data=leadership_io.getvalue(), file_name=leadership_filename)
