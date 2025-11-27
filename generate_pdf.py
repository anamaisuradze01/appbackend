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
    """
    Generate a professional CV PDF with AI-enhanced summary.
    
    Args:
        name: Full name of the person
        title: Target job title
        skills: List of skills
        experience: List of experience items
        style: Writing style (minimal, creative, formal, etc.)
        user_id: Unique user identifier
        
    Returns:
        Path to the generated PDF file
    """
    start_time = time.time()
    
    # 1️⃣ Generate AI summary (with fallback)
    summary_text = generate_summary_with_ai(name, title, skills, experience, style)
    
    # 2️⃣ Sanitize filename and create directory
    safe_title = re.sub(r"[^\w\d-]", "_", title)[:50]  # Limit length
    safe_user_id = re.sub(r"[^\w\d-]", "_", str(user_id))[:20]
    
    # Use /tmp for production environments (Render, Railway, etc.)
    pdf_dir = os.path.join("/tmp", "pdfs") if os.path.exists("/tmp") else os.path.join(os.getcwd(), "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    
    cv_id = f"cv_{safe_user_id}_{safe_title}_{int(time.time())}"
    pdf_path = os.path.join(pdf_dir, f"{cv_id}.pdf")
    
    # 3️⃣ Generate PDF
    try:
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=6,
            textColor=HexColor('#2c3e50'),
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=HexColor('#7f8c8d'),
            fontName='Helvetica'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=13,
            spaceAfter=6,
            spaceBefore=16,
            textColor=HexColor('#34495e'),
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leading=14
        )
        
        # Name and Title
        story.append(Paragraph(name, title_style))
        story.append(Paragraph(title, subtitle_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Summary Section (AI-generated)
        story.append(Paragraph("Professional Summary", heading_style))
        story.append(Paragraph(summary_text, normal_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Skills Section
        if skills:
            story.append(Paragraph("Skills", heading_style))
            skills_text = " • ".join(skills)
            story.append(Paragraph(skills_text, normal_style))
            story.append(Spacer(1, 0.1*inch))
        
        # Experience Section
        if experience:
            story.append(Paragraph("Experience", heading_style))
            for exp in experience:
                # Clean and format experience items
                exp_clean = exp.strip()
                if exp_clean:
                    story.append(Paragraph(f"• {exp_clean}", normal_style))
            story.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(story)
        
        execution_time = time.time() - start_time
        print(f"✅ CV generated successfully in {execution_time:.2f}s: {pdf_path}")
        
        return pdf_path
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        # Try basic fallback
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
    Falls back to template if API is unavailable.
    """
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY not set, using template summary")
        return generate_fallback_summary(name, title, skills, experience)
    
    prompt = f"""You are an expert CV/Resume writer. Generate a professional, concise CV summary.

### Input Data
* Name: {name}
* Target Job Title: {title}
* Key Skills: {', '.join(skills[:5])}
* Experience: {', '.join(experience[:3])}
* Style: {style}

### Instructions
1. Length: 3-4 sentences
2. Focus: Tailored to the target role ({title})
3. Content:
   - Opening: State role and experience level
   - Middle: Highlight 1-2 key achievements or skills
   - Closing: Value proposition or career goal
4. Tone: {style} and professional

Generate ONLY the summary text, no headings or extra formatting."""

    try:
        # Try to use Gemini API
        model = genai.GenerativeModel('gemini-1.5-flash')  # Use latest stable model
        response = model.generate_content(prompt)
        
        if response and response.text:
            summary_text = response.text.strip()
            print("✅ AI summary generated successfully")
            return summary_text
        else:
            print("⚠️ Empty AI response, using fallback")
            return generate_fallback_summary(name, title, skills, experience)
            
    except Exception as e:
        print(f"⚠️ Gemini API error: {e}, using fallback summary")
        return generate_fallback_summary(name, title, skills, experience)


def generate_fallback_summary(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str]
) -> str:
    """Generate a template-based summary when AI is unavailable."""
    top_skills = ', '.join(skills[:3]) if skills else "various technical skills"
    exp_highlight = experience[0] if experience else "proven track record of success"
    
    return f"""Motivated {title} with strong expertise in {top_skills}. 
Demonstrated experience in {exp_highlight}. 
Seeking to leverage technical skills and problem-solving abilities to drive innovation and deliver results in a dynamic environment."""


def generate_cv_basic(
    name: str,
    title: str,
    skills: List[str],
    experience: List[str],
    user_id: str = "default"
) -> str:
    """
    Fallback: Generate PDF using basic canvas if Platypus fails.
    """
    safe_title = re.sub(r"[^\w\d-]", "_", title)[:50]
    safe_user_id = re.sub(r"[^\w\d-]", "_", str(user_id))[:20]
    
    pdf_dir = os.path.join("/tmp", "pdfs") if os.path.exists("/tmp") else os.path.join(os.getcwd(), "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    
    cv_id = f"cv_{safe_user_id}_{safe_title}_{int(time.time())}"
    pdf_path = os.path.join(pdf_dir, f"{cv_id}.pdf")
    
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4
    
    # Current y position
    y = height - 50
    line_height = 14
    section_gap = 20
    
    # Name and Title
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, name)
    y -= line_height + 2
    
    c.setFont("Helvetica", 14)
    c.drawString(50, y, title)
    y -= section_gap
    
    # Summary
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "PROFESSIONAL SUMMARY")
    y -= line_height
    
    c.setFont("Helvetica", 10)
    summary = generate_fallback_summary(name, title, skills, experience)
    # Simple text wrapping
    words = summary.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        test_line = ' '.join(current_line)
        if len(test_line) > 80:
            lines.append(' '.join(current_line[:-1]))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    
    for line in lines:
        c.drawString(50, y, line)
        y -= line_height
    
    y -= section_gap - line_height
    
    # Skills
    if skills:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "SKILLS")
        y -= line_height
        
        c.setFont("Helvetica", 10)
        c.drawString(50, y, " • ".join(skills))
        y -= section_gap
    
    # Experience
    if experience:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "EXPERIENCE")
        y -= line_height
        
        c.setFont("Helvetica", 10)
        for exp in experience[:5]:  # Limit to 5 items
            c.drawString(50, y, f"• {exp[:100]}")  # Truncate long items
            y -= line_height
            if y < 50:
                break
    
    c.save()
    print(f"✅ Basic CV generated: {pdf_path}")
    return pdf_path
