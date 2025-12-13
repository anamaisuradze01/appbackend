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
            # Generate AI-enhanced skills if empty
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
    if not GEMINI_API_KEY:
        return generate_fallback_summary(name, title, skills, experience)
    
    prompt = f"""You are an expert CV writer. Generate a concise professional summary.

Name: {name}
Target Job Title: {title}
Key Skills: {', '.join(skills[:5])}
Experience: {', '.join(experience[:3])}
Style: {style}

Instructions:
- 3-4 sentences
- Focus on key achievements and value proposition
- Professional tone"""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip() if response and response.text else generate_fallback_summary(name, title, skills, experience)
    except Exception as e:
        print(f"⚠️ Gemini API error: {e}")
        return generate_fallback_summary(name, title, skills, experience)


def generate_skills_with_ai(skills: List[str], title: str, experience: List[str]) -> List[str]:
    """
    Generate an enhanced skills list using Gemini AI.
    """
    if not GEMINI_API_KEY:
        return skills if skills else ["Skill1", "Skill2", "Skill3"]
    
    prompt = f"""Generate a concise list of key skills for a {title} with experience: {', '.join(experience[:3])}.
Current skills: {', '.join(skills[:5]) if skills else 'None'}.
Return as a comma-separated list."""
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        if response and response.text:
            return [s.strip() for s in response.text.split(",") if s.strip()]
        return skills if skills else ["Skill1", "Skill2", "Skill3"]
    except Exception as e:
        print(f"⚠️ Gemini API error (skills): {e}")
        return skills if skills else ["Skill1", "Skill2", "Skill3"]


def generate_experience_description_with_ai(title: str, company: str, years: str, description: str = "") -> str:
    """
    Regenerate experience description using Gemini AI.
    """
    if not GEMINI_API_KEY:
        return description or "Describe your responsibilities and achievements."
    
    prompt = f"""Write a professional CV experience description.

Job Title: {title}
Company: {company}
Years: {years}
Current description: {description or 'None'}

Keep it concise, professional, and achievement-focused."""
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text.strip() if response and response.text else description
    except Exception as e:
        print(f"⚠️ Gemini API error (experience): {e}")
        return description
