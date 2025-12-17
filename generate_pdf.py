import os
import re
import time
from typing import List
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

# ----------------- Fallback summary -----------------
def generate_fallback_summary(title: str, skills: List[str], experience: List[str]) -> str:
    skills_str = ", ".join(skills[:3]) if skills else "relevant skills"
    exp_text = " ".join(experience[:2]) if experience else "experience in relevant roles"
    return f"A {title} with expertise in {skills_str}. Demonstrated achievements include {exp_text}. Proven ability to deliver results and contribute effectively to projects."

# ----------------- Skills generation -----------------
def generate_skills_with_ai(title: str, experience: List[str] = None) -> List[str]:
    """Generate professional skills based on title and optional experience."""
    if not client:
        return ["Communication", "Problem Solving", "Team Collaboration"]

    exp_summary = ', '.join(experience[:3]) if experience else 'None'

    prompt = f"""You are an expert CV writer.
Generate a list of 8-12 professional skills for someone with the job title: {title}.
Experience context: {exp_summary}
Instructions:
- Include both technical and soft skills
- Make them specific and relevant to the title
- Do NOT return numbers or explanations, only a comma-separated list of skills
- Skills should be actionable and reflect actual competencies"""

    try:
        response = client.models.generate_content(model='gemini-2.0-flash-exp', contents=prompt)
        if response and response.text:
            skills_generated = [s.strip() for s in response.text.strip().split(",") if s.strip()]
            return skills_generated if skills_generated else []
        return []
    except Exception as e:
        print(f"⚠️ Gemini API error (skills): {e}")
        return []

# ----------------- Experience description -----------------
def generate_experience_description_with_ai(title: str, company: str, years: str, description: str = "") -> str:
    """Generate detailed experience description, respecting user input if provided."""
    if not client:
        return description or "Responsible for key duties and achievements in this role."

    prompt = f"""You are a professional CV writer.
Generate a 2-3 sentence experience description for the following role:
Job Title: {title}
Company: {company}
Years: {years}
Current description (user-provided): {description or 'None'}
Instructions:
- Use the user-provided description as a base if available
- Highlight achievements, responsibilities, and impact
- Quantify results when possible
- Use professional tone, past tense
- Do NOT include markdown or headings
- Return only the description text"""

    try:
        response = client.models.generate_content(model='gemini-2.0-flash-exp', contents=prompt)
        return response.text.strip() if response and response.text else (description or "Responsible for key duties and achievements in this role.")
    except Exception as e:
        print(f"⚠️ Gemini API error (experience): {e}")
        return description or "Responsible for key duties and achievements in this role."

# ----------------- Summary generation -----------------
def generate_summary_with_ai(title: str, skills: List[str], experience: List[str], style: str = "minimal") -> str:
    """Generate a professional summary focused on achievements and skills."""
    if not client:
        return generate_fallback_summary(title, skills, experience)

    prompt = f"""You are an expert CV writer.
Generate a 3-4 sentence professional summary for someone with the job title: {title}.
Key Skills: {', '.join(skills[:5]) if skills else 'None'}
Experience Highlights: {', '.join(experience[:3]) if experience else 'None'}
Writing Style: {style}
Instructions:
- Integrate key skills naturally
- Highlight actual achievements or responsibilities
- Use experience highlights provided by the user if available
- Do NOT mention the user's name
- Avoid vague phrases and do NOT count experiences
- Confident, professional tone
- Return only the summary text"""

    try:
        response = client.models.generate_content(model='gemini-2.0-flash-exp', contents=prompt)
        return response.text.strip() if response and response.text else generate_fallback_summary(title, skills, experience)
    except Exception as e:
        print(f"⚠️ Gemini API error (summary): {e}")
        return generate_fallback_summary(title, skills, experience)

# ----------------- CV PDF generation -----------------
def generate_cv_gemini(title: str, skills: List[str], experience: List[str], style: str = "minimal", user_id: str = "default") -> str:
    """Generate a CV PDF with AI-enhanced summary, skills, and experience."""
    summary_text = generate_summary_with_ai(title, skills, experience, style)

    safe_title = re.sub(r"[^\w\d-]", "_", title)[:50]
    safe_user_id = re.sub(r"[^\w\d-]", "_", str(user_id))[:20]
    pdf_dir = os.path.join("/tmp", "pdfs") if os.path.exists("/tmp") else os.path.join(os.getcwd(), "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    cv_id = f"cv_{safe_user_id}_{safe_title}_{int(time.time())}"
    pdf_path = os.path.join(pdf_dir, f"{cv_id}.pdf")

    try:
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=20, spaceAfter=6, textColor=HexColor('#2c3e50'), fontName='Helvetica-Bold')
        subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'], fontSize=14, spaceAfter=12, textColor=HexColor('#7f8c8d'), fontName='Helvetica')
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=13, spaceAfter=6, spaceBefore=16, textColor=HexColor('#34495e'), fontName='Helvetica-Bold')
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6, leading=14)

        # Title section
        story.append(Paragraph(title, subtitle_style))
        story.append(Spacer(1, 0.1*inch))

        # Summary
        story.append(Paragraph("Professional Summary", heading_style))
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.1*inch))

        # Skills
        if skills:
            story.append(Paragraph("Skills", heading_style))
            story.append(Paragraph(" • ".join(skills), normal_style))
            story.append(Spacer(1, 0.1*inch))

        # Experience
        if experience:
            story.append(Paragraph("Experience", heading_style))
            for exp_text in experience:
                if exp_text.strip():
                    story.append(Paragraph(f"• {exp_text.strip()}", normal_style))
            story.append(Spacer(1, 0.1*inch))

        doc.build(story)
        print(f"✅ CV generated successfully: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        raise
