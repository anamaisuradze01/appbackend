import os
import re
import time
from typing import List, Dict, Any
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

# ----------------- Fallback summary -----------------
def generate_fallback_summary(title: str, skills: List[str], experience_list: List[Dict]) -> str:
    """Generate a better-than-nothing summary when AI fails"""
    
    # Count actual experience years if possible
    years_exp = "Entry-level" if not experience_list else f"{len(experience_list)}+"
    
    # Get top skills
    top_skills = ", ".join(skills[:4]) if skills else "various professional competencies"
    
    # Try to extract meaningful details from first experience
    exp_detail = ""
    if experience_list and len(experience_list) > 0:
        first_exp = experience_list[0]
        company = first_exp.get('company', '')
        role = first_exp.get('title', '')
        if company and role:
            exp_detail = f" Previously served as {role} at {company}, gaining practical experience in software development and testing."
    
    if experience_list and len(experience_list) > 0:
        return (
            f"{title} with hands-on experience in {top_skills}. "
            f"Demonstrated ability to deliver quality results across {len(experience_list)} professional role{'s' if len(experience_list) > 1 else ''}.{exp_detail} "
            f"Committed to continuous learning and professional excellence in quality assurance and software testing."
        )
    else:
        return (
            f"Motivated {title} with strong foundation in {top_skills}. "
            f"Eager to apply technical skills and contribute to software quality initiatives. "
            f"Quick learner with attention to detail and commitment to delivering high-quality results."
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
    """
    Generate a professional CV summary using Gemini AI.
    Does NOT include the person's name in the summary.
    """
    if not client:
        print("❌ GEMINI CLIENT NOT INITIALIZED - Check GEMINI_API_KEY")
        return generate_fallback_summary(title, skills, experience_list or [])
    
    print(f"✅ Gemini client is active, generating summary...")
    
    # Build comprehensive context
    experience_details = []
    if experience_list:
        for exp in experience_list:
            if exp.get('title') or exp.get('company'):
                exp_str = f"{exp.get('title', 'Role')} at {exp.get('company', 'Company')} ({exp.get('years', 'dates')})"
                if exp.get('description'):
                    exp_str += f": {exp.get('description')[:200]}"
                experience_details.append(exp_str)
    
    education_details = []
    if education_list:
        for edu in education_list:
            if edu.get('degree') or edu.get('school'):
                education_details.append(f"{edu.get('degree', 'Degree')} from {edu.get('school', 'Institution')} ({edu.get('years', 'dates')})")
    
    projects_details = []
    if projects_list:
        for proj in projects_list:
            if proj.get('name'):
                proj_str = f"{proj.get('name')}"
                if proj.get('description'):
                    proj_str += f": {proj.get('description')[:150]}"
                projects_details.append(proj_str)
    
    prompt = f"""You are an expert CV writer. Write a compelling professional summary for a CV.

CRITICAL RULES:
1. DO NOT include the person's name in the summary
2. Start with their current/target role and years of experience
3. Naturally weave in their skills with context (not just listing them)
4. Include specific achievements from their experience
5. Use quantified results when possible
6. Write 3-5 sentences in a natural, flowing style
7. Make it sound human-written, not robotic
8. Focus on value proposition and impact

TARGET ROLE: {title}

SKILLS: {', '.join(skills) if skills else 'Not provided'}

EXPERIENCE:
{chr(10).join(experience_details) if experience_details else 'No detailed experience provided'}

EDUCATION:
{chr(10).join(education_details) if education_details else 'Not provided'}

PROJECTS:
{chr(10).join(projects_details) if projects_details else 'Not provided'}

Write a professional summary that:
- Highlights their expertise in the target role
- Integrates skills naturally (e.g., "leveraging Python and SQL to optimize...", not "skills: Python, SQL")
- References specific accomplishments from their experience
- Includes education/projects if relevant and impressive
- Uses action-oriented language
- Sounds confident but not arrogant

Return ONLY the summary text, no formatting, no preamble."""

    try:
        print(f"📝 Generating summary with AI for: {title}")
        print(f"   Skills: {len(skills)} provided")
        print(f"   Experience: {len(experience_details)} entries")
        print(f"   Education: {len(education_details)} entries")
        
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        
        if response and response.text:
            summary = response.text.strip()
            print(f"✅ AI generated summary ({len(summary)} chars)")
            
            # Remove any markdown formatting
            summary = summary.replace('**', '').replace('*', '')
            # Remove any quotes
            summary = summary.strip('"').strip("'")
            
            # Safety check: remove name if AI included it
            if name and name in summary:
                summary = summary.replace(name, "").strip()
                # Clean up any double spaces or punctuation issues
                summary = ' '.join(summary.split())
            
            # Quality check - reject if too generic/short
            generic_phrases = [
                "strong foundation in",
                "committed to delivering high-quality",
                "continuous professional growth"
            ]
            is_generic = any(phrase in summary.lower() for phrase in generic_phrases)
            is_too_short = len(summary) < 200  # Strong summaries should be at least 200 chars
            
            if is_generic or is_too_short:
                print(f"⚠️ AI summary quality check failed (generic: {is_generic}, too short: {is_too_short})")
                print(f"   Falling back to template")
                return generate_fallback_summary(title, skills, experience_list or [])
            
            return summary
        else:
            print("⚠️ AI response was empty")
            return generate_fallback_summary(title, skills, experience_list or [])
        
    except Exception as e:
        print(f"❌ Gemini API error (summary): {e}")
        import traceback
        traceback.print_exc()
        return generate_fallback_summary(title, skills, experience_list or [])


# ----------------- Skills generation -----------------
def generate_skills_with_ai(skills: List[str], title: str, experience: List[str]) -> List[str]:
    """Generate an enhanced skills list using Gemini AI"""
    if not client:
        return skills if skills else ["Communication", "Problem Solving", "Team Collaboration"]
    
    current_skills = ', '.join(skills) if skills else 'None'
    exp_summary = '. '.join(experience[:3]) if experience else 'None'
    
    prompt = f"""Generate 10-15 relevant professional skills for a {title} position.

Current skills: {current_skills}
Experience context: {exp_summary}

Instructions:
- Include technical skills relevant to {title}
- Include important soft skills (leadership, communication, etc.)
- Mix specific technologies with broader competencies
- Make them specific and valuable
- Return ONLY a comma-separated list
- No explanations, no numbering, no quotes
- Example format: Python, Project Management, Data Analysis, Team Leadership

Generate the skills list now:"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        if response and response.text:
            text = response.text.strip().replace('**', '').replace('*', '')
            generated_skills = [s.strip() for s in text.split(",") if s.strip()]
            return generated_skills if generated_skills else (skills or [])
        return skills or []
    except Exception as e:
        print(f"⚠️ Gemini API error (skills): {e}")
        return skills or []


# ----------------- Experience description -----------------
def generate_experience_description_with_ai(title: str, company: str, years: str, description: str = "") -> str:
    """Generate professional experience description using Gemini AI"""
    if not client:
        return description or f"Responsible for key duties as {title} at {company}."

    prompt = f"""Write a professional CV experience description.

Position: {title}
Company: {company}
Duration: {years}
Current description: {description or 'None - please write from scratch'}

Instructions:
- Write 2-4 sentences describing key responsibilities and achievements
- Use strong action verbs (Led, Developed, Implemented, Managed, etc.)
- Include quantifiable results when possible (e.g., "increased efficiency by 25%", "managed team of 10")
- Focus on impact and value delivered
- Use past tense for completed roles, present tense for current roles
- Sound professional but natural
- DO NOT copy the current description word-for-word; enhance and improve it

Return ONLY the description, no formatting:"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        if response and response.text:
            desc = response.text.strip().replace('**', '').replace('*', '')
            desc = desc.strip('"').strip("'")
            return desc if desc else (description or f"Worked as {title} at {company}, contributing to key initiatives.")
        return description or f"Worked as {title} at {company}."
    except Exception as e:
        print(f"⚠️ Gemini API error (experience): {e}")
        return description or f"Worked as {title} at {company}."


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
    """Generate CV PDF with AI-enhanced content"""
    
    # Extract structured data if provided
    experience_list = []
    education_list = []
    projects_list = []
    
    if full_data:
        experience_list = full_data.get('experience', [])
        education_list = full_data.get('education', [])
        projects_list = full_data.get('projects', [])
    
    # Generate enhanced summary
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
        print(f"✅ CV generated: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        raise
