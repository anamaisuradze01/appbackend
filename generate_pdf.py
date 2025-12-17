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

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)


def generate_fallback_summary(name: str, title: str, skills: List[str], experience: List[str]) -> str:
    """
    Generate a basic summary without AI when API is unavailable.
    """
    skills_str = ", ".join(skills[:3]) if skills else "various technical skills"
    exp_count = len(experience) if experience else 0
    
    return (
        f"{name} is a {title} with expertise in {skills_str}. "
        f"With proven experience across {exp_count} positions, "
        f"brings a strong track record of delivering results and driving innovation."
    )


def generate_cv_basic(name: str, title: str, skills: List[str], experience: List[str], user_id: str = "default") -> str:
    """
    Generate a basic PDF without AI enhancement (fallback method).
    """
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
        
        # Basic summary
        summary = generate_fallback_summary(name, title, skills, experience)
        story.append(Paragraph("Professional Summary", heading_style))
        story.append(Paragraph(summary, normal_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Skills
        if skills:
            story.append(Paragraph("Skills", heading_style))
            skills_text = " • ".join(skills)
            story.append(Paragraph(skills_text, normal_style))
            story.append(Spacer(1, 0.1*inch))
        
        # Experience
        if experience:
            story.append(Paragraph("Experience", heading_style))
            for exp_text in experience:
                exp_clean = exp_text.strip()
                if exp_clean:
                    story.append(Paragraph(f"• {exp_clean}", normal_style))
            story.append(Spacer(1, 0.1*inch))
        
        doc.build(story)
        print(f"✅ Basic CV generated successfully: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"❌ Error generating basic PDF: {e}")
        raise


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
        
        # Summary
        story.append(Paragraph("Professional Summary", heading_style))
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Skills
        if skills:
            story.append(Paragraph("Skills", heading_style))
            skills_text = " • ".join(skills)
            story.append(Paragraph(skills_text, normal_style))
            story.append(Spacer(1, 0.1*inch))
        
        # Experience
        if experience:
            story.append(Paragraph("Experience", heading_style))
            for exp_text in experience:
                exp_clean = exp_text.strip()
                if exp_clean:
                    story.append(Paragraph(f"• {exp_clean}", normal_style))
            story.append(Spacer(1, 0.1*inch))
        
        doc.build(story)
        execution_time = time.time() - start_time
        print(f"✅ CV generated successfully in {execution_time:.2f}s: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        return generate_cv_basic(name, title, skills, experience, user_id)


def generate_summary_with_ai(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str],
    style: str = "minimal"
) -> str:
    """
    Generate a professional summary using Gemini AI.
    """
    if not client:
        print("⚠️ Gemini API not configured, using fallback summary")
        return generate_fallback_summary(name, title, skills, experience)
    
    prompt = f"""You are a senior CV writer and hiring manager.

Generate a concise, high-quality professional summary tailored specifically to the target job.

Input:
Name: {name}
Target Job Title: {title}
Key Skills (use at least 3 explicitly): {', '.join(skills[:5])}
Relevant Experience (derive achievements from these): {', '.join(experience[:3])}
Writing Style: {style}

Rules:

Write exactly 3–4 sentences

The summary MUST clearly match the Target Job Title

Explicitly reference relevant skills and experience (do NOT be generic)

If experience data is limited, infer realistic achievements based on the job title and skills

Do NOT mention missing data, placeholders, or counts (e.g., “0 positions”)

Avoid vague phrases like “various skills” or “strong background”

Use a confident, professional tone

Do NOT include markdown, bullet points, or headings

Return ONLY the summary text"""

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        return response.text.strip() if response and response.text else generate_fallback_summary(name, title, skills, experience)
    except Exception as e:
        print(f"⚠️ Gemini API error: {e}")
        return generate_fallback_summary(name, title, skills, experience)


def generate_skills_with_ai(skills: List[str], title: str, experience: List[str]) -> List[str]:
    """
    Generate an enhanced skills list using Gemini AI.
    """
    if not client:
        print("⚠️ Gemini API not configured, returning existing skills")
        return skills if skills else ["Communication", "Problem Solving", "Team Collaboration"]
    
    current_skills = ', '.join(skills[:5]) if skills else 'None'
    exp_summary = ', '.join(experience[:3]) if experience else 'None'
    
    prompt = f"""Generate a list of 8-12 relevant professional skills for a {title}.

Current skills: {current_skills}
Experience summary: {exp_summary}

Instructions:
- Return ONLY a comma-separated list of skills
- Include both technical and soft skills
- Make them specific and relevant to {title}
- No explanations, no numbering, just skills separated by commas
- Example format: Python, Leadership, Project Management, AWS"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        if response and response.text:
            generated_skills = [s.strip() for s in response.text.strip().split(",") if s.strip()]
            return generated_skills if generated_skills else skills
        return skills if skills else ["Communication", "Problem Solving", "Team Collaboration"]
    except Exception as e:
        print(f"⚠️ Gemini API error (skills): {e}")
        return skills if skills else ["Communication", "Problem Solving", "Team Collaboration"]


def generate_experience_description_with_ai(title: str, company: str, years: str, description: str = "") -> str:
    """
    Generate experience description using Gemini AI.
    """
    if not client:
        print("⚠️ Gemini API not configured, returning existing description")
        return description or "Responsible for key duties and achievements in this role."
    
    prompt = f"""Write a professional CV experience description for:

Job Title: {title}
Company: {company}
Years: {years}
Current description: {description or 'None provided'}

Instructions:
- Write 2-3 sentences describing responsibilities and achievements
- Use action verbs and quantify results when possible
- Professional tone, past tense for completed roles
- No markdown formatting
- Return only the description text"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        return response.text.strip() if response and response.text else (description or "Responsible for key duties and achievements in this role.")
    except Exception as e:
        print(f"⚠️ Gemini API error (experience): {e}")
        return description or "Responsible for key duties and achievements in this role."
