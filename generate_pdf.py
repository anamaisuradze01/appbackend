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
from google import genai
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ----------------- Summary -----------------
def generate_fallback_summary(name: str, title: str, skills: List[str], experience: List[str]) -> str:
    skills_str = ", ".join(skills[:3]) if skills else "various technical skills"
    exp_count = len(experience) if experience else 0
    return (
        f"{name} is a {title} with expertise in {skills_str}. "
        f"With proven experience across {exp_count} positions, "
        f"brings a strong track record of delivering results and driving innovation."
    )

def generate_summary_with_ai(name: str, title: str, skills: List[str], experience: List[str], style: str = "minimal") -> str:
    if not client:
        return generate_fallback_summary(name, title, skills, experience)
    
    prompt = f"""You are a senior CV writer.

Generate a concise professional summary.

Name: {name}
Target Job Title: {title}
Key Skills: {', '.join(skills[:5])}
Relevant Experience: {', '.join(experience[:3])}
Style: {style}

Write 3–4 sentences. Reference skills and experience. Return only the summary text."""

    try:
        response = client.models.generate_content(model='gemini-2.0-flash-exp', contents=prompt)
        return response.text.strip() if response and response.text else generate_fallback_summary(name, title, skills, experience)
    except Exception:
        return generate_fallback_summary(name, title, skills, experience)

# ----------------- Skills -----------------
def generate_skills_with_ai(title: str) -> List[str]:
    if not client:
        return ["Communication", "Problem Solving", "Team Collaboration"]

    prompt = f"""Generate a list of 8-12 relevant professional skills for a {title}.

Instructions:
- Return ONLY a comma-separated list of skills
- Include technical and soft skills
- Make them specific and relevant to the {title}"""

    try:
        response = client.models.generate_content(model='gemini-2.0-flash-exp', contents=prompt)
        if response and response.text:
            skills = [s.strip() for s in response.text.strip().split(",") if s.strip()]
            return skills if skills else ["Communication", "Problem Solving", "Team Collaboration"]
        return ["Communication", "Problem Solving", "Team Collaboration"]
    except Exception:
        return ["Communication", "Problem Solving", "Team Collaboration"]

# ----------------- Experience -----------------
def generate_experience_description_with_ai(title: str, company: str, years: str, description: str = "") -> str:
    if not client:
        return description or "Responsible for key duties and achievements."
    
    prompt = f"""Write a CV experience description for:

Job Title: {title}
Company: {company}
Years: {years}
Current description: {description or 'None'}

Instructions:
- 2-3 sentences
- Use action verbs
- Return only the description"""

    try:
        response = client.models.generate_content(model='gemini-2.0-flash-exp', contents=prompt)
        return response.text.strip() if response and response.text else (description or "Responsible for key duties and achievements.")
    except Exception:
        return description or "Responsible for key duties and achievements."

# ----------------- CV PDF Generation -----------------
def generate_cv_gemini(name: str, title: str, skills: List[str], experience: List[str], style: str = "minimal", user_id: str = "default") -> str:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor

    summary_text = generate_summary_with_ai(name, title, skills, experience, style)

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

        story.append(Paragraph(name, title_style))
        story.append(Paragraph(title, subtitle_style))
        story.append(Spacer(1, 0.1*inch))

        story.append(Paragraph("Professional Summary", heading_style))
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.1*inch))

        if skills:
            story.append(Paragraph("Skills", heading_style))
            story.append(Paragraph(" • ".join(skills), normal_style))
            story.append(Spacer(1, 0.1*inch))

        if experience:
            story.append(Paragraph("Experience", heading_style))
            for exp_text in experience:
                exp_clean = exp_text.strip()
                if exp_clean:
                    story.append(Paragraph(f"• {exp_clean}", normal_style))
            story.append(Spacer(1, 0.1*inch))

        doc.build(story)
        return pdf_path

    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        # fallback
        from generate_pdf import generate_cv_basic
        return generate_cv_basic(name, title, skills, experience, user_id)
