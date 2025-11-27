import os
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from linked_in_oauth import get_auth_url, get_access_token, get_linkedin_profile
from generate_pdf import generate_cv_gemini

load_dotenv()

app = FastAPI()

# ----------------- Session -----------------
# Simple in-memory session (use Redis/db for production)
SESSION = {}

# ----------------- CORS -----------------
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://linked-resumes.lovable.app")
origins = [
    FRONTEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Routes -----------------
@app.get("/")
def home():
    return {"message": "LinkedIn CV Generator API", "status": "running"}

@app.get("/login")
def login():
    """Redirect to LinkedIn OAuth"""
    return RedirectResponse(url=get_auth_url())

@app.get("/oauth/callback")
def callback(request: Request, code: str = None, error: str = None):
    """Handle LinkedIn OAuth callback"""
    if error or not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/?error={error or 'no_code'}")
    
    token_result = get_access_token(code)
    if "error" in token_result:
        return RedirectResponse(url=f"{FRONTEND_URL}/?error=token_failed")
    
    access_token = token_result.get("access_token")
    profile_result = get_linkedin_profile(access_token)
    if "error" in profile_result:
        return RedirectResponse(url=f"{FRONTEND_URL}/?error=profile_failed")
    
    # Store profile using user_id as key
    user_id = profile_result.get("id", "default")
    SESSION[user_id] = profile_result

    # Redirect to frontend CV editor
    return RedirectResponse(url=f"{FRONTEND_URL}/cv-editor?user_id={user_id}")

@app.get("/api/profile")
def get_profile(user_id: str = Query(None)):
    """Get LinkedIn profile data"""
    if not user_id:
        return JSONResponse(status_code=400, content={"error": "user_id required"})
    
    profile = SESSION.get(user_id)
    if not profile:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    
    return profile

@app.post("/generate_cv")
def generate_cv_endpoint(
    phone: str = Form(...),
    skills: str = Form(...),
    experience: str = Form(...),
    title: str = Form(...),
    user_id: str = Form(...)
):
    """Generate CV PDF"""
    profile = SESSION.get(user_id)
    if not profile:
        return JSONResponse(status_code=401, content={"error": "No profile found"})
    
    skills_list = [s.strip() for s in skills.split(",") if s.strip()]
    experience_list = [e.strip() for e in experience.split(",") if e.strip()]
    
    try:
        pdf_path = generate_cv_gemini(
            name=f"{profile.get('firstName', '')} {profile.get('lastName', '')}",
            title=title,
            skills=skills_list,
            experience=experience_list,
            style="minimal",
            user_id=user_id
        )
        
        return {"link": f"/download_cv?path={pdf_path}"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/download_cv")
def download_cv(path: str = Query(...)):
    """Download generated CV PDF"""
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(path, filename=os.path.basename(path))

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ----------------- Run -----------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
