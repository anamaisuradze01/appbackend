import os
import re
import time
from typing import List, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# ----------------- Gemini response helper -----------------
def extract_gemini_text(response) -> str | None:
    """Safely extract text from new google-genai response"""
    if not response or not getattr(response, "candidates", None):
        return None

    parts = response.candidates[0].content.parts
    text = "".join(
        part.text for part in parts if hasattr(part, "text") and part.text
    ).strip()

    return text or None


# ----------------- Fallback summary -----------------
def generate_fallback_summary(title: str, skills: List[str], experience_list: List[Dict]) -> str:
    years_exp = "Entry-level" if not experience_list else f"{len(experience_list)}+ years"
    top_skills = ", ".join(skills[:4]) if skills else "core technical skills"

    exp_detail = ""
    if experience_list:
        exp = experience_list[0]
        if exp.get("title") and exp.get("company"):
            exp_detail = f" Previously worked as {exp['title']} at {exp['company']}."

    return (
        f"{title} with {years_exp} of hands-on experience leveraging {top_skills}. "
        f"Demonstrates strong problem-solving ability, attention to detail, and a commitment to delivering reliable, high-quality software solutions."
        f"{exp_detail}"
    )


# ----------------- Summary generation -----------------
def generate_summary_with_ai(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str],
    style: str = "minimal",
    experience_list: List[Dict] = None,
    education_list: List[Dict] = None,
    projects_list: List[Dict] = None
) -> str:

    if not client:
        print("❌ Gemini client not initialized")
        return generate_fallback_summary(title, skills, experience_list or [])

    experience_details = []
    for exp in experience_list or []:
        line = f"{exp.get('title', '')} at {exp.get('company', '')} ({exp.get('years', '')})"
        if exp.get("description"):
            line += f": {exp['description'][:150]}"
        experience_details.append(line)

    education_details = [
        f"{e.get('degree', '')} — {e.get('school', '')}"
        for e in education_list or []
    ]

    projects_details = [
        f"{p.get('name')}: {p.get('description', '')[:120]}"
        for p in projects_list or []
        if p.get("name")
    ]

    prompt = f"""
You are a senior CV writer.

RULES:
- Do NOT include the person's name
- Write 3–5 sentences
- Start with role + experience level
- Integrate skills naturally
- Focus on impact and value
- Human, confident, professional tone

ROLE: {title}

SKILLS:
{", ".join(skills) if skills else "Not provided"}

EXPERIENCE:
{chr(10).join(experience_details) if experience_details else "Not provided"}

EDUCATION:
{chr(10).join(education_details) if education_details else "Not provided"}

PROJECTS:
{chr(10).join(projects_details) if projects_details else "Not provided"}

Return ONLY the summary text.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        summary = extract_gemini_text(response)

        if not summary:
            print("⚠️ Empty Gemini summary, using fallback")
            return generate_fallback_summary(title, skills, experience_list or [])

        # realistic quality gate
        if summary.count(".") < 2:
            print("⚠️ Gemini summary too weak, using fallback")
            return generate_fallback_summary(title, skills, experience_list or [])

        return summary

    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return generate_fallback_summary(title, skills, experience_list or [])


# ----------------- CV PDF generation -----------------
def generate_cv_gemini(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str],
    style: str = "minimal",
    user_id: str = "default",
    full_data: Dict[str, Any] = None
) -> str:

    experience_list = full_data.get("experience", []) if full_data else []
    education_list = full_data.get("education", []) if full_data else []
    projects_list = full_data.get("projects", []) if full_data else []

    summary_text = generate_summary_with_ai(
        name=name,
        title=title,
        skills=skills,
        experience=experience,
        style=style,
        experience_list=experience_list,
        education_list=education_list,
        projects_list=projects_list
    )

    safe_title = re.sub(r"[^\w\d-]", "_", title)[:50]
    safe_user_id = re.sub(r"[^\w\d-]", "_", str(user_id))[:20]

    pdf_dir = "/tmp/pdfs" if os.path.exists("/tmp") else "./pdfs"
    os.makedirs(pdf_dir, exist_ok=True)

    pdf_path = os.path.join(
        pdf_dir, f"cv_{safe_user_id}_{safe_title}_{int(time.time())}.pdf"
    )

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"], fontSize=20, textColor=HexColor("#2c3e50")
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Heading2"], fontSize=14, textColor=HexColor("#7f8c8d")
    )
    heading_style = ParagraphStyle(
        "Heading", parent=styles["Heading2"], fontSize=13, textColor=HexColor("#34495e")
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10, leading=14
    )

    story.append(Paragraph(name, title_style))
    story.append(Paragraph(title, subtitle_style))
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Professional Summary", heading_style))
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 0.15 * inch))

    if skills:
        story.append(Paragraph("Skills", heading_style))
        story.append(Paragraph(" • ".join(skills), body_style))

    if experience:
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph("Experience", heading_style))
        for exp in experience:
            story.append(Paragraph(f"• {exp}", body_style))

    doc.build(story)
    print(f"✅ CV generated: {pdf_path}")
    return pdf_path
