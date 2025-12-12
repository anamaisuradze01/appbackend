import os
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from linked_in_oauth import get_auth_url, get_access_token, get_linkedin_profile
from generate_pdf import generate_cv_gemini, regenerate_field_ai

app = FastAPI()

SESSION = {}

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://linked-resumes.lovable.app")
origins = [FRONTEND_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "LinkedIn CV Generator API", "status": "running"}

# ---------------------- NEW ENDPOINT ----------------------
@app.post("/regenerate_field")
async def regenerate_field(
    field: str = Form(...),
    index: int = Form(default=None),
    fullName: str = Form(""),
    title: str = Form(""),
    summary: str = Form(""),
    skills: str = Form(""),
    experience: str = Form(""),
):
    """
    Regenerate individual field sections:
      - skills
      - summary
      - experience[index]
    """
    try:
        skills_list = [s.strip() for s in skills.split(",") if s.strip()]
        exp_list = [e.strip() for e in experience.split("|||") if e.strip()]

        result = regenerate_field_ai(
            field=field,
            index=index,
            name=fullName,
            title=title,
            summary=summary,
            skills=skills_list,
            experience=exp_list
        )

        return {"result": result}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ----------------------------------------------------------

@app.post("/generate_cv")
def generate_cv_endpoint(
    phone: str = Form(...),
    skills: str = Form(...),
    experience: str = Form(...),
    title: str = Form(...),
    user_id: str = Form(...)
):
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
    if not os.path.exists(path):
        return JSONResponse(status_code=404, content={"error": "File not found"})
    return FileResponse(path, filename=os.path.basename(path))
