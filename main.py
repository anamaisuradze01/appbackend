import os
from fastapi import FastAPI, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
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

# ----------------- Pydantic Models -----------------
class ExperienceData(BaseModel):
    title: str = ""
    company: str = ""
    years: str = ""
    description: str = ""

class RegenerateRequest(BaseModel):
    user_id: str
    field: str
    index: Optional[int] = None
    experience_data: Optional[ExperienceData] = None
    current_data: Optional[Dict[str, Any]] = None

# ----------------- Helper Functions -----------------
def initialize_user_data(profile_result: dict) -> dict:
    """Initialize user data structure with profile and empty CV fields"""
    return {
        "name": profile_result.get("name", ""),
        "firstName": profile_result.get("firstName", ""),
        "lastName": profile_result.get("lastName", ""),
        "email": profile_result.get("email", ""),
        "id": profile_result.get("id", ""),
        "picture": profile_result.get("picture", ""),

        "fullName": profile_result.get("name", ""),
        "title": "",
        "phone": "",
        "location": "",
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
        "languages": []
    }

# ----------------- OAuth -----------------
@app.get("/login")
def login():
    return RedirectResponse(url=get_auth_url())

@app.get("/oauth/callback")
def callback(request: Request, code: str = None, error: str = None):
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
    SESSION[user_id] = initialize_user_data(profile_result)
    return RedirectResponse(url=f"{frontend_url}/cv-editor?user_id={user_id}")

@app.get("/api/profile")
def get_profile(user_id: str = Query(None)):
    if not user_id or user_id not in SESSION:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing user_id"})
    return JSONResponse(content=SESSION[user_id])

# ----------------- CV Endpoints -----------------
@app.post("/api/clear")
def clear_cv(user_id: str = Query(...)):
    if not user_id or user_id not in SESSION:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing user_id"})
    
    user_data = SESSION[user_id]
    user_data.update({
        "fullName": user_data.get("name", ""),
        "title": "",
        "phone": "",
        "location": "",
        "summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
        "languages": []
    })
    SESSION[user_id] = user_data
    return JSONResponse(content={"status": "cleared", "data": user_data})

@app.post("/api/regenerate")
def regenerate_field(request: RegenerateRequest):
    user_id = request.user_id
    field = request.field
    index = request.index

    if not user_id or user_id not in SESSION:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing user_id"})

    user_data = SESSION[user_id]

    # Update session with current form data to ensure AI sees latest inputs
    if request.current_data:
        print(f"🔹 Received current_data for regeneration ({field}): {request.current_data}")
        user_data.update(request.current_data)
        SESSION[user_id] = user_data

    try:
        if field == "summary":
            regenerated_summary = generate_summary_with_ai(
                name=user_data.get("fullName", ""),
                title=user_data.get("title", "Professional"),
                skills=user_data.get("skills", []),
                experience=[e.get("description", "") for e in user_data.get("experience", [])],
                style="minimal"
            )
            return JSONResponse(content={"status": "ok", "field": "summary", "value": regenerated_summary})

        elif field == "skills":
            regenerated_skills = generate_skills_with_ai(
                skills=user_data.get("skills", []),
                title=user_data.get("title", "Professional"),
                experience=[e.get("description", "") for e in user_data.get("experience", [])]
            )
            return JSONResponse(content={"status": "ok", "field": "skills", "value": regenerated_skills})

        elif field == "experience":
            if index is None:
                return JSONResponse(status_code=400, content={"error": "Experience index is required"})

            # Use latest experience data from request if provided
            if request.experience_data:
                exp_item = request.experience_data.dict()
            else:
                if index >= len(user_data.get("experience", [])):
                    return JSONResponse(status_code=400, content={"error": f"Invalid experience index {index}"})
                exp_item = user_data["experience"][index]

            regenerated_description = generate_experience_description_with_ai(
                title=exp_item.get("title", ""),
                company=exp_item.get("company", ""),
                years=exp_item.get("years", ""),
                description=exp_item.get("description", "")
            )
            return JSONResponse(content={"status": "ok", "field": "experience", "index": index, "value": regenerated_description})

        else:
            return JSONResponse(status_code=400, content={"error": f"Unknown field '{field}'"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Failed to regenerate {field}: {str(e)}"})

# ----------------- Generate CV PDF -----------------
@app.post("/api/generate_cv")
def generate_cv(user_id: str = Query(...)):
    if not user_id or user_id not in SESSION:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing user_id"})

    user_data = SESSION[user_id]

    skills = user_data.get("skills", [])
    experience = [e.get("description", "") for e in user_data.get("experience", [])]

    try:
        pdf_path = generate_cv_gemini(
            name=user_data.get("fullName", ""),
            title=user_data.get("title", ""),
            skills=skills,
            experience=experience,
            style="minimal",
            user_id=user_id
        )
        return JSONResponse(content={"status": "ok", "pdf_path": pdf_path})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to generate CV: {str(e)}"})

# ----------------- Download CV -----------------
@app.get("/api/download_cv")
def download_cv(path: str = Query(...)):
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(path, filename=os.path.basename(path), media_type="application/pdf")

# ----------------- Health Check -----------------
@app.get("/")
def root():
    gemini_status = "configured" if os.getenv("GEMINI_API_KEY") else "not configured"
    return {"status": "running", "gemini_api": gemini_status, "frontend_url": FRONTEND_URL}

@app.get("/health")
def health():
    return {"status": "healthy"}
