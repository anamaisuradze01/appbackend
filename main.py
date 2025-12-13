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

# ----------------- Helper Functions -----------------
def initialize_user_data(profile_result: dict) -> dict:
    """Initialize user data structure with profile and empty CV fields"""
    return {
        # LinkedIn profile data
        "name": profile_result.get("name", ""),
        "firstName": profile_result.get("firstName", ""),
        "lastName": profile_result.get("lastName", ""),
        "email": profile_result.get("email", ""),
        "id": profile_result.get("id", ""),
        "picture": profile_result.get("picture", ""),
        
        # CV data structure
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
    """Handle LinkedIn OAuth callback"""
    frontend_url = FRONTEND_URL
    if error:
        return RedirectResponse(url=f"{frontend_url}?error={error}")
    if not code:
        return RedirectResponse(url=f"{frontend_url}?error=no_code")

    token_result = get_access_token(code)
    if "error" in token_result:
        print(f"Token error: {token_result}")
        return RedirectResponse(url=f"{frontend_url}?error=token_failed")

    access_token = token_result.get("access_token")
    profile_result = get_linkedin_profile(access_token)
    if "error" in profile_result:
        print(f"Profile error: {profile_result}")
        return RedirectResponse(url=f"{frontend_url}?error=profile_failed")

    user_id = profile_result.get("id", "default")
    SESSION[user_id] = initialize_user_data(profile_result)
    
    print(f"✅ User {user_id} logged in successfully")
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
    
    # Keep LinkedIn profile data but clear CV fields
    user_data = SESSION[user_id]
    user_data.update({
        "fullName": user_data.get("name", ""),  # Keep name from profile
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
    print(f"✅ Cleared CV data for user {user_id}")
    return JSONResponse(content={"status": "cleared", "data": user_data})

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
    print(f"🔄 Regenerating {field} for user {user_id}")

    try:
        if field == "summary":
            user_data["summary"] = generate_summary_with_ai(
                name=user_data.get("fullName", ""),
                title=user_data.get("title", "Professional"),
                skills=user_data.get("skills", []),
                experience=[e.get("description", "") for e in user_data.get("experience", [])],
                style="minimal"
            )
            print(f"✅ Generated summary: {user_data['summary'][:100]}...")
            
        elif field == "skills":
            user_data["skills"] = generate_skills_with_ai(
                skills=user_data.get("skills", []),
                title=user_data.get("title", "Professional"),
                experience=[e.get("description", "") for e in user_data.get("experience", [])]
            )
            print(f"✅ Generated {len(user_data['skills'])} skills")
            
        elif field == "experience":
            if index is None:
                return JSONResponse(status_code=400, content={"error": "Experience index is required"})
            
            if index >= len(user_data.get("experience", [])):
                return JSONResponse(status_code=400, content={"error": f"Invalid experience index {index}"})
            
            exp_item = user_data["experience"][index]
            exp_item["description"] = generate_experience_description_with_ai(
                title=exp_item.get("title", ""),
                company=exp_item.get("company", ""),
                years=exp_item.get("years", ""),
                description=exp_item.get("description", "")
            )
            print(f"✅ Generated experience description for {exp_item.get('title', 'position')}")
            
        else:
            return JSONResponse(status_code=400, content={"error": f"Unknown field '{field}'"})

        SESSION[user_id] = user_data
        return JSONResponse(content={"status": "ok", "data": user_data})
        
    except Exception as e:
        print(f"❌ Error regenerating {field}: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to regenerate {field}: {str(e)}"})

# ----------------- Generate CV PDF -----------------
@app.post("/api/generate_cv")
def generate_cv(user_id: str = Query(...)):
    """Generate CV PDF using Gemini AI (Tailored to Title)"""
    if not user_id or user_id not in SESSION:
        return JSONResponse(status_code=400, content={"error": "Invalid or missing user_id"})

    user_data = SESSION[user_id]
    
    # Validate required fields
    if not user_data.get("fullName"):
        return JSONResponse(status_code=400, content={"error": "Full name is required"})
    
    if not user_data.get("title"):
        return JSONResponse(status_code=400, content={"error": "Professional title is required"})
    
    try:
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
        
        print(f"✅ CV generated for user {user_id}: {pdf_path}")
        return JSONResponse(content={"status": "ok", "pdf_path": pdf_path})
        
    except Exception as e:
        print(f"❌ Error generating CV: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to generate CV: {str(e)}"})

# ----------------- Download CV -----------------
@app.get("/api/download_cv")
def download_cv(path: str = Query(...)):
    """Download generated CV PDF"""
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(path, filename=os.path.basename(path), media_type="application/pdf")

# ----------------- Health Check -----------------
@app.get("/")
def root():
    """Health check endpoint"""
    gemini_status = "configured" if os.getenv("GEMINI_API_KEY") else "not configured"
    return {
        "status": "running",
        "gemini_api": gemini_status,
        "frontend_url": FRONTEND_URL
    }

@app.get("/health")
def health():
    """Health check for monitoring"""
    return {"status": "healthy"}
