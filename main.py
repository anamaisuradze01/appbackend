import os
from fastapi import FastAPI, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# At the top of main.py, add this:
print("🔍 Loading generate_pdf module...")
from generate_pdf import (
    generate_cv_gemini,
    generate_summary_with_ai,
    generate_skills_with_ai,
    generate_experience_description_with_ai
)
print("🔍 Checking Gemini client in imported module...")


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


class EducationData(BaseModel):
    school: str = ""
    degree: str = ""
    years: str = ""


class ProjectData(BaseModel):
    name: str = ""
    description: str = ""


class ProfileData(BaseModel):
    fullName: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: List[str] = []
    experience: List[ExperienceData] = []
    education: List[EducationData] = []
    projects: List[ProjectData] = []
    languages: List[str] = []


class RegenerateRequest(BaseModel):
    user_id: str
    field: str
    index: Optional[int] = None
    experience_data: Optional[ExperienceData] = None
    current_data: Optional[Dict[str, Any]] = None


class GenerateCVRequest(BaseModel):
    user_id: str
    data: ProfileData


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

    # Update session with current data from frontend
    if request.current_data:
        # Deep merge the current_data to preserve all fields
        for key, value in request.current_data.items():
            user_data[key] = value
        SESSION[user_id] = user_data

    try:
        if field == "summary":
            # Extract experience list properly
            experience_list = user_data.get("experience", [])
            education_list = user_data.get("education", [])
            projects_list = user_data.get("projects", [])

            summary = generate_summary_with_ai(
                name=user_data.get("fullName", ""),
                title=user_data.get("title", ""),
                skills=user_data.get("skills", []),
                experience=[e.get("description", "") for e in experience_list],
                experience_list=experience_list,
                education_list=education_list,
                projects_list=projects_list
            )

            # Update session with new summary
            user_data["summary"] = summary
            SESSION[user_id] = user_data

            return JSONResponse(content={"status": "ok", "field": "summary", "value": summary})

        elif field == "skills":
            skills = generate_skills_with_ai(
                title=user_data.get("title", ""),
                experience=[e.get("description", "") for e in user_data.get("experience", [])],
                current_skills=user_data.get("skills", [])
            )

            # Update session with new skills
            user_data["skills"] = skills
            SESSION[user_id] = user_data

            return JSONResponse(content={"status": "ok", "field": "skills", "value": skills})

        elif field == "experience":
            if index is None:
                return JSONResponse(status_code=400, content={"error": "Experience index is required"})

            # Get experience item from request or session
            if request.experience_data:
                exp_item = request.experience_data.dict()
            else:
                if index >= len(user_data.get("experience", [])):
                    return JSONResponse(status_code=400, content={"error": f"Invalid experience index {index}"})
                exp_item = user_data["experience"][index]

            description = generate_experience_description_with_ai(
                title=exp_item.get("title", ""),
                company=exp_item.get("company", ""),
                years=exp_item.get("years", ""),
                description=exp_item.get("description", "")
            )

            # Update session with new description
            if index < len(user_data.get("experience", [])):
                user_data["experience"][index]["description"] = description
                SESSION[user_id] = user_data

            return JSONResponse(content={"status": "ok", "field": "experience", "index": index, "value": description})

        else:
            return JSONResponse(status_code=400, content={"error": f"Unknown field '{field}'"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Failed to regenerate {field}: {str(e)}"})


# ----------------- Generate CV PDF -----------------
@app.post("/api/generate_cv")
def generate_cv(request: GenerateCVRequest):
    user_id = request.user_id
    data = request.data

    if not user_id or user_id not in SESSION:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing user_id"})

    if not data.fullName or not data.title:
        return JSONResponse(status_code=400, content={"error": "Full name and Professional title are required"})

    try:
        # Convert Pydantic models to dicts for PDF generation
        full_data = {
            "fullName": data.fullName,
            "title": data.title,
            "email": data.email,
            "phone": data.phone,
            "location": data.location,
            "summary": data.summary,
            "skills": data.skills,
            "experience": [exp.dict() for exp in data.experience],
            "education": [edu.dict() for edu in data.education],
            "projects": [proj.dict() for proj in data.projects],
            "languages": data.languages
        }

        # Update session with latest data
        SESSION[user_id].update(full_data)

        pdf_path = generate_cv_gemini(
            name=data.fullName,
            title=data.title,
            skills=data.skills,
            experience=[e.description for e in data.experience],
            style="minimal",
            user_id=user_id,
            full_data=full_data
        )

        return JSONResponse(content={"status": "ok", "pdf_path": pdf_path})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Failed to generate CV: {str(e)}"})


@app.get("/api/download_cv")
def download_cv(path: str = Query(...)):
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(path, filename=os.path.basename(path), media_type="application/pdf")


@app.get("/")
def root():
    gemini_status = "configured" if os.getenv("GEMINI_API_KEY") else "not configured"
    return {"status": "running", "gemini_api": gemini_status, "frontend_url": FRONTEND_URL}


@app.get("/health")
def health():
    return {"status": "healthy"}


# Add this Pydantic model
class TailorCVRequest(BaseModel):
    user_id: str
    job_title: str
    current_data: Dict[str, Any]


# Add this endpoint
@app.post("/api/tailor")
def tailor_cv(request: TailorCVRequest):
    user_id = request.user_id
    job_title = request.job_title
    current_data = request.current_data

    if not user_id:
        return JSONResponse(status_code=400, content={"error": "User ID is required"})

    if not job_title:
        return JSONResponse(status_code=400, content={"error": "Job title is required"})

    try:
        # Extract data from current_data
        full_name = current_data.get("fullName", "")
        current_title = current_data.get("title", "")
        skills = current_data.get("skills", [])
        experience_list = current_data.get("experience", [])
        education_list = current_data.get("education", [])
        projects_list = current_data.get("projects", [])

        # Use AI to generate tailored summary
        tailored_summary = generate_summary_with_ai(
            name=full_name,
            title=job_title,  # Use the NEW job title
            skills=skills,
            experience=[exp.get("description", "") for exp in experience_list],
            experience_list=experience_list,
            education_list=education_list,
            projects_list=projects_list
        )

        # Use AI to generate tailored skills for the new job title
        experience_texts = [exp.get("description", "") for exp in experience_list]
        tailored_skills = generate_skills_with_ai(
            title=job_title,  # Use the NEW job title
            experience=experience_texts,
            current_skills=skills
        )

        # Create tailored data response
        tailored_data = {
            **current_data,
            "title": job_title,  # Update the title
            "summary": tailored_summary,
            "skills": tailored_skills,
        }

        # Update session if user exists
        if user_id in SESSION:
            SESSION[user_id].update(tailored_data)

        return JSONResponse(content={
            "status": "ok",
            "message": f"CV tailored for {job_title}",
            "tailored_data": tailored_data
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to tailor CV: {str(e)}"}
        )
