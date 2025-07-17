# === FULL FIXED SCRIPT (FORMATTING REPAIRED) ===
import streamlit as st
from openai import OpenAI
from docx import Document
from docx.shared import Pt
from io import BytesIO
from datetime import date
import requests
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt

# === PAGE CONFIG ===
st.set_page_config(page_title="Mestek Coaching Generator", layout="wide")

# === PASSWORD ===
PASSWORD = "WFHQmestek413"
if st.text_input("Enter password:", type="password") != PASSWORD:
    st.warning("Please enter the correct password.")
    st.stop()

# === GOOGLE SCRIPT URL ===
SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzphJdM4C4-fQ8OS1Q_2eW7sXsC12MKPthejioPoDg_gnUlImkzOcKJM5_ndk9KzQewNg/exec"

# === HELPERS ===
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
    for field in [
        "Date of Incident", "Department", "Employee Name", "Supervisor Name",
        "Action Taken", "Issue Type", "Incident Description", "Estimated/Annual Cost",
        "Language Spoken", "Previous Coaching/Warnings"]:
        add_bold_para(doc, field + ":", latest.get(field, "[Missing]"))

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
        "My signature below does not necessarily indicate agreement but confirms that I have received and reviewed this documentation.")
    doc.add_paragraph("Employee Signature: _________________________        Date: ________________")
    doc.add_paragraph("Supervisor Signature: ________________________        Date: ________________")
    return doc

def build_leadership_doc(latest, leadership_text):
    doc = Document()
    doc.add_heading("Leadership Reflection", 0)
    for field in ["Supervisor Name", "Employee Name", "Department", "Issue Type", "Date of Incident"]:
        add_bold_para(doc, field + ":", latest.get(field, "[Missing]"))

    doc.add_paragraph()
    add_section_header(doc, "AI-Generated Leadership Guidance:")

    sections = [
        "Private Reflection", "Coaching Tips", "Tone Guidance",
        "Follow-Up Recommendation", "Supervisor Accountability Tip"]

    current_section = None
    buffer = []

    for line in leadership_text.splitlines():
        stripped = line.strip()
        if stripped.endswith(":") and stripped[:-1] in sections:
            if current_section and buffer:
                add_section_header(doc, current_section + ":")
                doc.add_paragraph(" ".join(buffer).strip())
                buffer = []
            current_section = stripped[:-1]
        elif current_section:
            buffer.append(stripped)

    if current_section and buffer:
        add_section_header(doc, current_section + ":")
        doc.add_paragraph(" ".join(buffer).strip())

    return doc
