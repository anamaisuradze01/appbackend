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

# Load environment variables
load_dotenv()

# Get API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY not found in environment!")
    print("   Make sure your .env file has: GEMINI_API_KEY=your_actual_key_here")
    client = None
else:
    print(f"✅ API Key found: {GEMINI_API_KEY[:10]}...{GEMINI_API_KEY[-4:]}")
    client = genai.Client(api_key=GEMINI_API_KEY)


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


# ----------------- Fallback generators -----------------
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


def generate_fallback_skills(title: str) -> List[str]:
    """Generate fallback skills based on job title"""
    common_skills = ["Problem Solving", "Team Collaboration", "Communication", "Time Management"]

    # Add title-specific skills
    title_lower = title.lower()
    if any(word in title_lower for word in ["developer", "engineer", "programmer"]):
        return ["Python", "JavaScript", "Git", "API Development"] + common_skills
    elif any(word in title_lower for word in ["designer", "ux", "ui"]):
        return ["Figma", "Adobe XD", "User Research", "Prototyping"] + common_skills
    elif any(word in title_lower for word in ["manager", "lead", "director"]):
        return ["Leadership", "Strategic Planning", "Budget Management", "Stakeholder Communication"]

    return common_skills


def generate_fallback_experience_description(title: str, company: str, current_desc: str) -> str:
    """Generate fallback experience description"""
    if current_desc and len(current_desc) > 20:
        return current_desc

    return (
        f"Contributed to key projects at {company} in the role of {title}. "
        f"Collaborated with cross-functional teams to deliver high-quality results. "
        f"Applied technical expertise and problem-solving skills to overcome challenges."
    )


# ----------------- AI Summary Generation -----------------
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
    """Generate professional summary using AI"""

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

        # Quality gate
        if summary.count(".") < 2:
            print("⚠️ Gemini summary too weak, using fallback")
            return generate_fallback_summary(title, skills, experience_list or [])

        return summary

    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return generate_fallback_summary(title, skills, experience_list or [])


# ----------------- AI Skills Generation -----------------
def generate_skills_with_ai(
        title: str,
        experience: List[str],
        current_skills: List[str] = None
) -> List[str]:
    """Generate skills list using AI based on title and experience"""

    if not client:
        print("❌ Gemini client not initialized")
        return generate_fallback_skills(title)

    prompt = f"""
You are a CV skills expert.

RULES:
- Generate 6-12 relevant professional skills
- Mix technical and soft skills appropriately for the role
- Return ONLY a comma-separated list of skills
- No explanations, no numbering, just: "Skill1, Skill2, Skill3"

ROLE: {title}

CURRENT SKILLS (if any): {", ".join(current_skills or [])}

EXPERIENCE CONTEXT:
{chr(10).join(experience[:3]) if experience else "No experience provided"}

Return ONLY the comma-separated skills list.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        skills_text = extract_gemini_text(response)

        if not skills_text:
            print("⚠️ Empty Gemini skills, using fallback")
            return generate_fallback_skills(title)

        # Parse skills
        skills = [s.strip() for s in skills_text.split(",") if s.strip()]

        if len(skills) < 3:
            print("⚠️ Too few skills generated, using fallback")
            return generate_fallback_skills(title)

        return skills[:12]  # Limit to 12 skills

    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return generate_fallback_skills(title)


# ----------------- AI Experience Description Generation -----------------
def generate_experience_description_with_ai(
        title: str,
        company: str,
        years: str,
        description: str = ""
) -> str:
    """Generate experience description using AI"""

    if not client:
        print("❌ Gemini client not initialized")
        return generate_fallback_experience_description(title, company, description)

    prompt = f"""
You are a CV writing expert.

RULES:
- Write 2-4 sentences describing this work experience
- Focus on responsibilities, achievements, and impact
- Use professional, action-oriented language
- Be specific but concise
- Return ONLY the description text

POSITION: {title}
COMPANY: {company}
DURATION: {years}
CURRENT DESCRIPTION (if any): {description or "None provided"}

Return ONLY the experience description.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        new_description = extract_gemini_text(response)

        if not new_description or len(new_description) < 50:
            print("⚠️ Weak Gemini description, using fallback")
            return generate_fallback_experience_description(title, company, description)

        return new_description

    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return generate_fallback_experience_description(title, company, description)


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
    """Generate CV PDF with complete data structure"""

    # Use full_data if provided, otherwise create basic structure
    if full_data:
        experience_list = full_data.get("experience", [])
        education_list = full_data.get("education", [])
        projects_list = full_data.get("projects", [])
        languages_list = full_data.get("languages", [])
        phone = full_data.get("phone", "")
        location = full_data.get("location", "")
        email = full_data.get("email", "")
        summary_text = full_data.get("summary", "")
    else:
        experience_list = []
        education_list = []
        projects_list = []
        languages_list = []
        phone = ""
        location = ""
        email = ""
        summary_text = ""

    # Generate summary if not provided
    if not summary_text:
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

    # Custom styles matching the frontend design
    title_style = ParagraphStyle(
        "Title", parent=styles["Heading1"], fontSize=24, textColor=HexColor("#1a1a1a"), spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=styles["Heading2"], fontSize=16, textColor=HexColor("#4a5568"), spaceAfter=12
    )
    contact_style = ParagraphStyle(
        "Contact", parent=styles["Normal"], fontSize=10, textColor=HexColor("#718096")
    )
    heading_style = ParagraphStyle(
        "Heading", parent=styles["Heading2"], fontSize=13, textColor=HexColor("#2d3748"),
        spaceAfter=8, spaceBefore=12, fontName="Helvetica-Bold"
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"], fontSize=10, leading=14, textColor=HexColor("#2d3748")
    )
    job_title_style = ParagraphStyle(
        "JobTitle", parent=styles["Normal"], fontSize=11, textColor=HexColor("#2d3748"), fontName="Helvetica-Bold"
    )
    company_style = ParagraphStyle(
        "Company", parent=styles["Normal"], fontSize=10, textColor=HexColor("#4a5568"), fontName="Helvetica-Bold"
    )

    # Header
    story.append(Paragraph(name, title_style))
    story.append(Paragraph(title, subtitle_style))

    # Contact info
    contact_parts = []
    if email:
        contact_parts.append(f"✉ {email}")
    if phone:
        contact_parts.append(f"☎ {phone}")
    if location:
        contact_parts.append(f"📍 {location}")

    if contact_parts:
        story.append(Paragraph(" • ".join(contact_parts), contact_style))

    story.append(Spacer(1, 0.2 * inch))

    # Summary
    if summary_text:
        story.append(Paragraph("SUMMARY", heading_style))
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 0.15 * inch))

    # Experience
    if experience_list:
        story.append(Paragraph("EXPERIENCE", heading_style))
        for exp in experience_list:
            exp_title = exp.get("title", "")
            exp_company = exp.get("company", "")
            exp_years = exp.get("years", "")
            exp_desc = exp.get("description", "")

            if exp_title and exp_company:
                story.append(Paragraph(f"{exp_title} — {exp_years}", job_title_style))
                story.append(Paragraph(exp_company, company_style))
                if exp_desc:
                    story.append(Paragraph(exp_desc, body_style))
                story.append(Spacer(1, 0.1 * inch))
        story.append(Spacer(1, 0.05 * inch))

    # Education
    if education_list:
        story.append(Paragraph("EDUCATION", heading_style))
        for edu in education_list:
            edu_school = edu.get("school", "")
            edu_degree = edu.get("degree", "")
            edu_years = edu.get("years", "")

            if edu_school:
                story.append(Paragraph(f"{edu_school} — {edu_years}", job_title_style))
                if edu_degree:
                    story.append(Paragraph(edu_degree, body_style))
                story.append(Spacer(1, 0.1 * inch))
        story.append(Spacer(1, 0.05 * inch))

    # Skills
    if skills:
        story.append(Paragraph("SKILLS", heading_style))
        story.append(Paragraph(" • ".join(skills), body_style))
        story.append(Spacer(1, 0.15 * inch))

    # Projects
    if projects_list:
        story.append(Paragraph("PROJECTS", heading_style))
        for proj in projects_list:
            proj_name = proj.get("name", "")
            proj_desc = proj.get("description", "")

            if proj_name:
                story.append(Paragraph(proj_name, job_title_style))
                if proj_desc:
                    story.append(Paragraph(proj_desc, body_style))
                story.append(Spacer(1, 0.1 * inch))
        story.append(Spacer(1, 0.05 * inch))

    # Languages
    if languages_list:
        story.append(Paragraph("LANGUAGES", heading_style))
        story.append(Paragraph(" • ".join(languages_list), body_style))

    doc.build(story)
    print(f"✅ CV generated: {pdf_path}")
    return pdf_path

