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

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def generate_summary_with_ai(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str],
    style: str = "minimal"
) -> str:
    """
    Generate a professional summary using Gemini AI.
    Falls back to template if API is unavailable.
    """
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY not set. Using fallback summary.")
        return generate_fallback_summary(name, title, skills, experience)

    prompt = f"""
You are an expert CV writer. Generate a concise, professional CV summary.

### Input
Name: {name}
Job Title: {title}
Skills: {', '.join(skills[:5])}
Experience: {', '.join(experience[:3])}
Style: {style}

### Requirements
- 3–4 sentences
- Tailored to the job title "{title}"
- No headings or markdown
- Professional tone
"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        if response and response.text:
            print("✅ AI summary generated.")
            return response.text.strip()

        print("⚠️ Gemini response empty. Using fallback summary.")
        return generate_fallback_summary(name, title, skills, experience)

    except Exception as e:
        print(f"⚠️ Gemini API error: {e}")
        return generate_fallback_summary(name, title, skills, experience)


def generate_fallback_summary(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str]
) -> str:
    top_skills = ", ".join(skills[:3]) if skills else "core professional competencies"
    exp_highlight = experience[0] if experience else "a proven ability to deliver results"

    return (
        f"{title} professional skilled in {top_skills}. "
        f"Experience includes {exp_highlight}. "
        f"Committed to contributing value through strong problem-solving and adaptability."
    )


def generate_cv_gemini(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str],
    style: str = "minimal",
    user_id: str = "default"
) -> str:
    start_time = time.time()

    summary_text = generate_summary_with_ai(name, title, skills, experience, style)

    safe_title = re.sub(r"[^\w\d-]", "_", title)[:50]
    safe_user_id = re.sub(r"[^\w\d-]", "_", str(user_id))[:20]

    pdf_dir = "/tmp/pdfs" if os.path.exists("/tmp") else os.path.join(os.getcwd(), "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)

    cv_id = f"cv_{safe_user_id}_{safe_title}_{int(time.time())}"
    pdf_path = os.path.join(pdf_dir, f"{cv_id}.pdf")

    try:
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=HexColor("#2c3e50"),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=HexColor("#7f8c8d"),
            spaceAfter=12
        )
        heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=HexColor("#34495e"),
            spaceBefore=16,
            spaceAfter=6
        )
        normal_style = ParagraphStyle(
            'NormalStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceAfter=6
        )

        # Header
        story.append(Paragraph(name, title_style))
        story.append(Paragraph(title, subtitle_style))
        story.append(Spacer(1, 0.1 * inch))

        # Summary
        story.append(Paragraph("Professional Summary", heading_style))
        story.append(Paragraph(summary_text, normal_style))

        # Skills
        if skills:
            story.append(Paragraph("Skills", heading_style))
            story.append(Paragraph(" • ".join(skills), normal_style))

        # Experience
        if experience:
            story.append(Paragraph("Experience", heading_style))
            for exp in experience:
                clean = exp.strip()
                if clean:
                    story.append(Paragraph(f"• {clean}", normal_style))

        doc.build(story)
        print(f"✅ CV generated in {time.time() - start_time:.2f}s: {pdf_path}")
        return pdf_path

    except Exception as e:
        print(f"❌ Platypus error: {e}. Using basic fallback.")
        return generate_cv_basic(name, title, skills, experience, user_id)


def generate_cv_basic(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str],
    user_id: str = "default"
) -> str:
    safe_title = re.sub(r"[^\w\d-]", "_", title)[:50]
    safe_user_id = re.sub(r"[^\w\d-]", "_", user_id)[:20]

    pdf_dir = "/tmp/pdfs" if os.path.exists("/tmp") else os.path.join(os.getcwd(), "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)

    cv_id = f"cv_{safe_user_id}_{safe_title}_{int(time.time())}"
    pdf_path = os.path.join(pdf_dir, f"{cv_id}.pdf")

    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    y = height - 50
    line_height = 14

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, name)
    y -= 20
    c.setFont("Helvetica", 14)
    c.drawString(50, y, title)
    y -= 30

    # Summary
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "PROFESSIONAL SUMMARY")
    y -= 18
    c.setFont("Helvetica", 10)
    summary = generate_fallback_summary(name, title, skills, experience)
    for line in wrap_text(summary, 90):
        c.drawString(50, y, line)
        y -= line_height
    y -= 20

    # Skills
    if skills:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "SKILLS")
        y -= 18
        c.setFont("Helvetica", 10)
        for line in wrap_text(" • ".join(skills), 90):
            c.drawString(50, y, line)
            y -= line_height
        y -= 20

    # Experience
    if experience:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "EXPERIENCE")
        y -= 18
        c.setFont("Helvetica", 10)
        for exp in experience[:5]:
            for line in wrap_text("• " + exp, 90):
                c.drawString(50, y, line)
                y -= line_height

    c.save()
    print(f"✅ Basic CV generated: {pdf_path}")
    return pdf_path


def wrap_text(text: str, max_chars: int):
    """Simple text wrapper for basic PDF fallback."""
    words = text.split()
    lines = []
    current = []

    for w in words:
        current.append(w)
        if len(" ".join(current)) > max_chars:
            lines.append(" ".join(current[:-1]))
            current = [w]

    if current:
        lines.append(" ".join(current))

    return lines
