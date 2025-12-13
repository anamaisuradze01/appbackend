import os
from fastapi import FastAPI, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from linked_in_oauth import get_auth_url, get_access_token, get_linkedin_profile
from generate_pdf import (
    generate_cv_gemini,
    generate_summary_with_ai,
    generate_skills_with_ai,
    generate_experience_description_with_ai
)

app = FastAPI()

# ----------------- In-memory session -----------------
SESSION = {}

# ----------------- CORS -----------------
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://linked-resumes.lovable.app")
origins = [FRONTEND_URL]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- OAuth -----------------
@app.get("/login")
def login():
    return RedirectResponse(url=get_auth_url())

@app.get("/oauth/callback")
def callback(request: Request, code: str = None, error: str = None):
    """Handle LinkedIn OAuth callback"""
    frontend_url = FRONTEND_URL
    if error:
        return RedirectResponse(url=f"{frontend_url}?error={error}")
    if not code:
        return RedirectResponse(url=f"{frontend_url}?error=no_code")

    token_result = get_access_token(code)
    if "error" in token_result:
        return RedirectResponse(url=f"{frontend_url}?error=token_failed")

    access_token = token_result.get("access_token")
    profile_result = get_linkedin_profile(access_token)
    if "error" in profile_result:
        return RedirectResponse(url=f"{frontend_url}?error=profile_failed")

    user_id = profile_result.get("id", "default")
    SESSION[user_id] = profile_result
    return RedirectResponse(url=f"{frontend_url}/cv-editor?user_id={user_id}")

@app.get("/api/profile")
def get_profile(user_id: str = Query(None)):
    """Get LinkedIn profile data as JSON"""
    if not user_id or user_id not in SESSION:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing user_id"})
    return JSONResponse(content=SESSION[user_id])

# ----------------- CV Endpoints -----------------
@app.post("/api/clear")
def clear_cv(user_id: str = Query(...)):
    """Clear all CV fields for the given user"""
    if not user_id or user_id not in SESSION:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing user_id"})
    
    SESSION[user_id] = {
        "fullName": "",
        "title": "",
        "email": "",
        "phone": "",
        "location": "",
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
        "languages": []
    }
    return JSONResponse(content={"status": "cleared", "data": SESSION[user_id]})

@app.post("/api/regenerate")
def regenerate_field(
    user_id: str = Query(...),
    field: str = Query(...),
    index: int = Query(None)
):
    """Regenerate AI content for summary, skills, or experience"""
    if not user_id or user_id not in SESSION:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing user_id"})
    
    user_data = SESSION[user_id]

    if field == "summary":
        user_data["summary"] = generate_summary_with_ai(
            name=user_data.get("fullName", ""),
            title=user_data.get("title", ""),
            skills=user_data.get("skills", []),
            experience=[e.get("description", "") for e in user_data.get("experience", [])],
            style="minimal"
        )
    elif field == "skills":
        user_data["skills"] = generate_skills_with_ai(
            skills=user_data.get("skills", []),
            title=user_data.get("title", ""),
            experience=[e.get("description", "") for e in user_data.get("experience", [])]
        )
    elif field == "experience":
        if index is None or index >= len(user_data.get("experience", [])):
            return JSONResponse(status_code=400, content={"error": "Invalid experience index"})
        exp_item = user_data["experience"][index]
        exp_item["description"] = generate_experience_description_with_ai(
            title=exp_item.get("title", ""),
            company=exp_item.get("company", ""),
            years=exp_item.get("years", ""),
            description=exp_item.get("description", "")
        )
    else:
        return JSONResponse(status_code=400, content={"error": f"Unknown field '{field}'"})

    SESSION[user_id] = user_data
    return JSONResponse(content={"status": "ok", "data": user_data})

# ----------------- Generate CV PDF -----------------
@app.post("/api/generate_cv")
def generate_cv(user_id: str = Query(...)):
    """Generate CV PDF using Gemini AI (Tailored to Title)"""
    if not user_id or user_id not in SESSION:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing user_id"})

    user_data = SESSION[user_id]
    skills = user_data.get("skills", [])
    experience = [e.get("description", "") for e in user_data.get("experience", [])]

    pdf_path = generate_cv_gemini(
        name=user_data.get("fullName", ""),
        title=user_data.get("title", ""),
        skills=skills,
        experience=experience,
        style="minimal",
        user_id=user_id
    )
    return JSONResponse(content={"status": "ok", "pdf_path": pdf_path})

# ----------------- Download CV -----------------
@app.get("/api/download_cv")
def download_cv(path: str = Query(...)):
    """Download generated CV PDF"""
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(path, filename=os.path.basename(path))
