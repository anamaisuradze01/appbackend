import os
import re
import time
from typing import List
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ---------------- AI SUMMARY ----------------

def generate_summary_with_ai(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str],
    style: str = "minimal"
) -> str:
    if not GEMINI_API_KEY:
        return generate_fallback_summary(name, title, skills, experience)

    prompt = f"""
You are an expert CV writer.

Name: {name}
Target Role: {title}
Skills: {', '.join(skills[:5])}
Experience: {', '.join(experience[:3])}
Style: {style}

Generate a 3–4 sentence professional summary.
No headings. Professional tone.
"""

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception:
        pass

    return generate_fallback_summary(name, title, skills, experience)


def generate_fallback_summary(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str]
) -> str:
    top_skills = ", ".join(skills[:3]) if skills else "core professional competencies"
    exp_highlight = experience[0] if experience else "a strong record of delivering results"

    return (
        f"{title} professional skilled in {top_skills}. "
        f"Experience includes {exp_highlight}. "
        f"Focused on delivering value through adaptability and problem-solving."
    )


# ---------------- PDF GENERATION ----------------

def generate_cv_gemini(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str],
    style: str = "minimal",
    user_id: str = "default"
) -> str:
    summary_text = generate_summary_with_ai(name, title, skills, experience, style)

    safe_title = re.sub(r"[^\w\d-]", "_", title)[:50]
    safe_user = re.sub(r"[^\w\d-]", "_", str(user_id))[:20]

    pdf_dir = "/tmp/pdfs" if os.path.exists("/tmp") else "pdfs"
    os.makedirs(pdf_dir, exist_ok=True)

    pdf_path = os.path.join(
        pdf_dir, f"cv_{safe_user}_{safe_title}_{int(time.time())}.pdf"
    )

    try:
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontSize=22,
            textColor=HexColor("#2c3e50")
        )
        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=HexColor("#7f8c8d")
        )
        heading_style = ParagraphStyle(
            "Heading",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=HexColor("#34495e")
        )
        normal_style = ParagraphStyle(
            "Normal",
            parent=styles["Normal"],
            fontSize=10,
            leading=14
        )

        story.append(Paragraph(name, title_style))
        story.append(Paragraph(title, subtitle_style))
        story.append(Spacer(1, 0.1 * inch))

        story.append(Paragraph("Professional Summary", heading_style))
        story.append(Paragraph(summary_text, normal_style))

        if skills:
            story.append(Paragraph("Skills", heading_style))
            story.append(Paragraph(" • ".join(skills), normal_style))

        if experience:
            story.append(Paragraph("Experience", heading_style))
            for exp in experience:
                if exp.strip():
                    story.append(Paragraph(f"• {exp.strip()}", normal_style))

        doc.build(story)
        return pdf_path

    except Exception:
        return generate_cv_basic(name, title, skills, experience, user_id)


# ---------------- BASIC FALLBACK ----------------

def generate_cv_basic(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str],
    user_id: str = "default"
) -> str:
    safe_title = re.sub(r"[^\w\d-]", "_", title)[:50]
    safe_user = re.sub(r"[^\w\d-]", "_", str(user_id))[:20]

    pdf_dir = "/tmp/pdfs" if os.path.exists("/tmp") else "pdfs"
    os.makedirs(pdf_dir, exist_ok=True)

    pdf_path = os.path.join(
        pdf_dir, f"cv_{safe_user}_{safe_title}_{int(time.time())}.pdf"
    )

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, name)
    y -= 20

    c.setFont("Helvetica", 14)
    c.drawString(50, y, title)
    y -= 30

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "PROFESSIONAL SUMMARY")
    y -= 18

    c.setFont("Helvetica", 10)
    for line in wrap_text(generate_fallback_summary(name, title, skills, experience), 90):
        c.drawString(50, y, line)
        y -= 14

    c.save()
    return pdf_path


# ---------------- FIELD REGENERATION (FIXES IMPORT ERROR) ----------------

def regenerate_field_ai(
    field: str,
    index: int,
    name: str,
    title: str,
    summary: str,
    skills: List[str],
    experience: List[str]
) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")

    if field == "summary":
        prompt = f"""
Rewrite this CV summary.

Target Role: {title}
Current Summary: {summary}

3–4 sentences. Professional tone.
"""

    elif field == "skills":
        prompt = f"""
Rewrite the skills list for a {title}.

Current Skills: {", ".join(skills)}

Return comma-separated skills only.
"""

    elif field == "experience":
        if index is None or index >= len(experience):
            raise ValueError("Invalid experience index")

        prompt = f"""
Rewrite this CV experience entry.

Target Role: {title}
Experience: {experience[index]}

1–2 concise, achievement-focused sentences.
"""

    else:
        raise ValueError("Unsupported field")

    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)

    if not response or not response.text:
        raise RuntimeError("AI generation failed")

    return response.text.strip()


# ---------------- UTIL ----------------

def wrap_text(text: str, max_chars: int):
    words = text.split()
    lines = []
    current = []

    for word in words:
        current.append(word)
        if len(" ".join(current)) > max_chars:
            lines.append(" ".join(current[:-1]))
            current = [word]

    if current:
        lines.append(" ".join(current))

    return lines
