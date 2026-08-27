from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Depends,
    HTTPException,
    Security
)
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)
from sqlalchemy.orm import Session
from pypdf import PdfReader
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware

import psycopg
import os
import jwt

from datetime import datetime, timedelta, timezone

from .database import Base, engine, get_db
from . import models


# =========================================================
# APP SETUP
# =========================================================

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

bearer_scheme = HTTPBearer()

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# =========================================================
# JWT SETTINGS
# =========================================================

SECRET_KEY = "careerlens-development-secret-change-later"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =========================================================
# CREATE ACCESS TOKEN
# =========================================================

def create_access_token(user_id: int):

    expire = datetime.now(
        timezone.utc
    ) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# =========================================================
# GET CURRENT USER
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(
        bearer_scheme
    ),
    db: Session = Depends(get_db)
):

    token = credentials.credentials

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:

            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

        user = (
            db.query(models.User)
            .filter(
                models.User.id == int(user_id)
            )
            .first()
        )

        if user is None:

            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        return user

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health_check():

    return {
        "status": "ok"
    }


# =========================================================
# DATABASE TEST
# =========================================================

@app.get("/db-test")
def database_test():

    connection = psycopg.connect(
        "dbname=careerlens_db"
    )

    connection.close()

    return {
        "database": "connected"
    }


# =========================================================
# REGISTER
# =========================================================

@app.post("/register")
def register(
    name: str,
    email: str,
    password: str,
    db: Session = Depends(get_db)
):

    existing_user = (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )

    if existing_user:

        return {
            "error": "Email already registered"
        }

    hashed_password = pwd_context.hash(
        password
    )

    user = models.User(
        name=name,
        email=email,
        password=hashed_password
    )

    db.add(user)

    db.commit()

    db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email
    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/login")
def login(
    email: str,
    password: str,
    db: Session = Depends(get_db)
):

    user = (
        db.query(models.User)
        .filter(
            models.User.email == email
        )
        .first()
    )

    if user is None:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not pwd_context.verify(
        password,
        user.password
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        user.id
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "id": user.id,
        "name": user.name,
        "email": user.email
    }


# =========================================================
# JOB ROLES
# =========================================================

JOB_ROLES = {

    "Java Backend Developer": [
        "Java",
        "Spring Boot",
        "SQL",
        "Git",
        "REST API",
        "Docker"
    ],

    "Python Backend Developer": [
        "Python",
        "FastAPI",
        "SQL",
        "Git",
        "REST API",
        "Docker"
    ],

    "Frontend Developer": [
        "HTML",
        "CSS",
        "JavaScript",
        "React",
        "Git"
    ],

    "Data Analyst": [
        "Python",
        "SQL",
        "Excel",
        "Power BI",
        "Statistics"
    ]
}


# =========================================================
# GET JOB REQUIREMENTS
# =========================================================

@app.get("/job-requirements")
def job_requirements(
    title: str
):

    required_skills = JOB_ROLES.get(
        title
    )

    if required_skills is None:

        return {
            "error": "Job role not found"
        }

    return {
        "title": title,
        "required_skills": required_skills
    }


# =========================================================
# CREATE JOB
# =========================================================

@app.post("/create-job")
def create_job(
    title: str,
    required_skills: str
):

    skills = [
        skill.strip()
        for skill in required_skills.split(",")
        if skill.strip()
    ]

    return {
        "title": title,
        "required_skills": skills
    }


# =========================================================
# SKILL EXTRACTION
# =========================================================

def extract_skills(text):

    skills = [

        "Python",
        "Java",
        "JavaScript",
        "HTML",
        "CSS",
        "React",
        "FastAPI",
        "SQL",
        "MySQL",
        "PostgreSQL",
        "Git",
        "GitHub",
        "Spring Boot",
        "REST API",
        "Docker",
        "AWS",
        "Excel",
        "Power BI",
        "Statistics",
        "Machine Learning",
        "TensorFlow",
        "PyTorch",
        "Kubernetes",
        "Linux",
        "Azure",
        "GCP"
    ]

    found_skills = []

    text_lower = text.lower()

    for skill in skills:

        if skill.lower() in text_lower:

            found_skills.append(skill)

    return found_skills


# =========================================================
# JOB DESCRIPTION SKILL EXTRACTION
# =========================================================

def extract_job_skills(job_description):
    """
    Detect skills from either:
    1. A job role such as "Frontend Developer"
    2. A complete job description
    """

    text = job_description.lower().strip()

    # =========================================================
    # ROLE -> REQUIRED SKILLS
    # =========================================================

    role_skills = {

        # ---------------- FRONTEND ----------------
        "frontend developer": [
            "HTML",
            "CSS",
            "JavaScript",
            "React",
            "Git"
        ],

        "front end developer": [
            "HTML",
            "CSS",
            "JavaScript",
            "React",
            "Git"
        ],

        "web developer": [
            "HTML",
            "CSS",
            "JavaScript",
            "React",
            "Git"
        ],

        # ---------------- BACKEND ----------------
        "backend developer": [
            "Python",
            "FastAPI",
            "Flask",
            "SQL",
            "REST API",
            "Git"
        ],

        "back end developer": [
            "Python",
            "FastAPI",
            "Flask",
            "SQL",
            "REST API",
            "Git"
        ],

        "python developer": [
            "Python",
            "FastAPI",
            "Flask",
            "SQL",
            "REST API",
            "Git"
        ],

        # ---------------- FULL STACK ----------------
        "full stack developer": [
            "HTML",
            "CSS",
            "JavaScript",
            "React",
            "Python",
            "FastAPI",
            "SQL",
            "REST API",
            "Git"
        ],

        "fullstack developer": [
            "HTML",
            "CSS",
            "JavaScript",
            "React",
            "Python",
            "FastAPI",
            "SQL",
            "REST API",
            "Git"
        ],

        # ---------------- DATA ----------------
        "data analyst": [
            "Python",
            "SQL",
            "Excel",
            "Pandas",
            "Statistics",
            "Power BI"
        ],

        "data scientist": [
            "Python",
            "SQL",
            "Pandas",
            "NumPy",
            "Statistics",
            "Machine Learning"
        ],

        # ---------------- AI / ML ----------------
        "machine learning engineer": [
            "Python",
            "Machine Learning",
            "Statistics",
            "TensorFlow",
            "PyTorch",
            "SQL",
            "Git"
        ],

        "machine learning developer": [
            "Python",
            "Machine Learning",
            "Statistics",
            "TensorFlow",
            "PyTorch",
            "SQL",
            "Git"
        ],

        "ai engineer": [
            "Python",
            "Machine Learning",
            "Deep Learning",
            "TensorFlow",
            "PyTorch",
            "SQL",
            "Git"
        ],

        "ai/ml engineer": [
            "Python",
            "Machine Learning",
            "Deep Learning",
            "TensorFlow",
            "PyTorch",
            "SQL",
            "Git"
        ],

        "aiml engineer": [
            "Python",
            "Machine Learning",
            "Deep Learning",
            "TensorFlow",
            "PyTorch",
            "SQL",
            "Git"
        ],

        # ---------------- SOFTWARE ----------------
        "software developer": [
            "Python",
            "SQL",
            "Git",
            "REST API",
            "Data Structures and Algorithms"
        ],

        "software engineer": [
            "Python",
            "SQL",
            "Git",
            "REST API",
            "Data Structures and Algorithms"
        ],

        # ---------------- DEVOPS / CLOUD ----------------
        "devops engineer": [
            "Linux",
            "Docker",
            "Kubernetes",
            "Git",
            "AWS"
        ],

        "cloud engineer": [
            "AWS",
            "Linux",
            "Docker",
            "Git"
        ],

        # ---------------- DATABASE ----------------
        "database administrator": [
            "SQL",
            "MySQL",
            "PostgreSQL",
            "Linux"
        ],

        "database developer": [
            "SQL",
            "MySQL",
            "PostgreSQL"
        ],

        # ---------------- CYBERSECURITY ----------------
        "cybersecurity analyst": [
            "Linux",
            "Networking",
            "Python",
            "SQL"
        ],

        # ---------------- MOBILE ----------------
        "mobile app developer": [
            "JavaScript",
            "React"
        ],

        # ---------------- JAVA ----------------
        "java developer": [
            "Java",
            "SQL",
            "Spring Boot",
            "REST API",
            "Git"
        ]
    }

    # =========================================================
    # NORMALIZE ROLE INPUT
    # =========================================================

    role_aliases = {

        "frontend": "frontend developer",
        "front end": "frontend developer",
        "front-end developer": "frontend developer",
        "front end developer": "frontend developer",

        "backend": "backend developer",
        "back end": "backend developer",
        "back-end developer": "backend developer",
        "back end developer": "backend developer",

        "fullstack": "full stack developer",
        "full-stack developer": "full stack developer",

        "python": "python developer",

        "data analytics": "data analyst",
        "data analysis": "data analyst",

        "ml engineer": "machine learning engineer",
        "ml developer": "machine learning developer",

        "ai engineer": "ai engineer",
        "ai ml engineer": "ai/ml engineer",
        "ai/ml": "ai/ml engineer"
    }

    # Check direct alias
    if text in role_aliases:
        text = role_aliases[text]

    # Check exact role
    if text in role_skills:
        return role_skills[text]

    # Check whether a role appears inside the input
    # Example:
    # "I am looking for a frontend developer"
    # "Looking for Python Developer"
    for role, skills in role_skills.items():

        if role in text:
            return skills

    # =========================================================
    # FALLBACK:
    # EXTRACT SKILLS FROM A FULL JOB DESCRIPTION
    # =========================================================

    available_skills = [
        "Python",
        "Java",
        "JavaScript",
        "HTML",
        "CSS",
        "React",
        "FastAPI",
        "Flask",
        "SQL",
        "MySQL",
        "PostgreSQL",
        "Git",
        "GitHub",
        "Spring Boot",
        "REST API",
        "Docker",
        "AWS",
        "Excel",
        "Power BI",
        "Statistics",
        "Machine Learning",
        "Deep Learning",
        "TensorFlow",
        "PyTorch",
        "Kubernetes",
        "Linux",
        "Azure",
        "GCP"
    ]

    found_skills = []

    for skill in available_skills:

        if skill.lower() in text:
            found_skills.append(skill)

    return found_skills
# =========================================================
# ANALYZE RESUME AGAINST CUSTOM JOB DESCRIPTION
# =========================================================

@app.post("/analyze-custom-job")
def analyze_custom_job(
    resume_id: int,
    job_description: str,
    current_user: models.User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    # Get the logged-in user's resume
    resume_record = (
        db.query(models.Resume)
        .filter(
            models.Resume.id == resume_id,
            models.Resume.user_id == current_user.id
        )
        .first()
    )

    if resume_record is None:
        raise HTTPException(
            status_code=404,
            detail="Resume not found"
        )

    # Extract skills from resume
    resume_skills = extract_skills(
        resume_record.resume_text or ""
    )

    # Extract skills from job description
    required_skills = extract_job_skills(
        job_description
    )

    resume = {
        skill.lower()
        for skill in resume_skills
    }

    required = {
        skill.lower()
        for skill in required_skills
    }

    matched = resume.intersection(
        required
    )

    missing = required - resume

    match_percentage = 0

    if required:
        match_percentage = round(
            (len(matched) / len(required)) * 100
        )

    recommendations_list = []

    for skill in missing:
        recommendations_list.append(
            f"Learn {skill} and build a small project using it."
        )

    # Save analysis
    analysis = models.Analysis(
        resume_id=resume_record.id,
        job_title="Custom Job Description",
        match_percentage=match_percentage,
        matched_skills=", ".join(
            sorted(matched)
        ),
        missing_skills=", ".join(
            sorted(missing)
        ),
        recommendations=", ".join(
            recommendations_list
        )
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return {
        "analysis_id": analysis.id,
        "resume_id": resume_record.id,
        "job_title": "Custom Job Description",
        "required_skills": sorted(required),
        "resume_skills": sorted(resume),
        "match_percentage": match_percentage,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "recommendations": recommendations_list
    }

# =========================================================
# MATCH SKILLS
# =========================================================

@app.post("/match-skills")
def match_skills(
    resume_skills: str,
    required_skills: str
):

    resume = {
        skill.strip().lower()
        for skill in resume_skills.split(",")
        if skill.strip()
    }

    required = {
        skill.strip().lower()
        for skill in required_skills.split(",")
        if skill.strip()
    }

    matched = resume.intersection(
        required
    )

    missing = required - resume

    match_percentage = 0

    if required:

        match_percentage = round(
            (len(matched) / len(required)) * 100,
            2
        )

    return {
        "match_percentage": match_percentage,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing)
    }


# =========================================================
# RECOMMENDATIONS
# =========================================================

@app.post("/recommendations")
def recommendations(
    missing_skills: str
):

    recommendations_list = []

    for skill in missing_skills.split(","):

        skill = skill.strip()

        if not skill:
            continue

        recommendations_list.append(
            f"Learn {skill} and build a small project using it."
        )

    return {
        "recommendations": recommendations_list
    }


# =========================================================
# MANUAL ANALYZE
# =========================================================

@app.post("/analyze")
def analyze_resume(
    resume_skills: str,
    job_title: str,
    resume_id: int,
    db: Session = Depends(get_db)
):

    required_skills = JOB_ROLES.get(
        job_title
    )

    if required_skills is None:

        return {
            "error": "Job role not found"
        }

    resume = {
        skill.strip().lower()
        for skill in resume_skills.split(",")
        if skill.strip()
    }

    required = {
        skill.strip().lower()
        for skill in required_skills
        if skill.strip()
    }

    matched = resume.intersection(
        required
    )

    missing = required - resume

    match_percentage = 0

    if required:

        match_percentage = round(
            (len(matched) / len(required)) * 100
        )

    recommendations_list = []

    for skill in missing:

        recommendations_list.append(
            f"Learn {skill} and build a small project using it."
        )

    analysis = models.Analysis(
        resume_id=resume_id,
        job_title=job_title,
        match_percentage=match_percentage,
        matched_skills=", ".join(
            sorted(matched)
        ),
        missing_skills=", ".join(
            sorted(missing)
        ),
        recommendations=", ".join(
            recommendations_list
        )
    )

    db.add(analysis)

    db.commit()

    db.refresh(analysis)

    return {
        "analysis_id": analysis.id,
        "job_title": job_title,
        "match_percentage": match_percentage,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "recommendations": recommendations_list
    }


# =========================================================
# GET ALL ANALYSES
# =========================================================

@app.get("/analyses")
def get_analyses(
    db: Session = Depends(get_db)
):

    analyses = db.query(
        models.Analysis
    ).all()

    return [

        {
            "id": analysis.id,
            "resume_id": analysis.resume_id,
            "job_title": analysis.job_title,
            "match_percentage": analysis.match_percentage,
            "matched_skills": analysis.matched_skills,
            "missing_skills": analysis.missing_skills,
            "recommendations": analysis.recommendations
        }

        for analysis in analyses
    ]


# =========================================================
# ANALYZE SAVED RESUME
# =========================================================

@app.post("/analyze-resume")
def analyze_uploaded_resume(
    resume_id: int,
    job_title: str,
    db: Session = Depends(get_db)
):

    resume_record = (
        db.query(models.Resume)
        .filter(
            models.Resume.id == resume_id
        )
        .first()
    )

    if resume_record is None:

        return {
            "error": "Resume not found"
        }

    required_skills = JOB_ROLES.get(
        job_title
    )

    if required_skills is None:

        return {
            "error": "Job role not found"
        }

    resume_skills = extract_skills(
        resume_record.resume_text or ""
    )

    resume = {
        skill.strip().lower()
        for skill in resume_skills
        if skill.strip()
    }

    required = {
        skill.strip().lower()
        for skill in required_skills
        if skill.strip()
    }

    matched = resume.intersection(
        required
    )

    missing = required - resume

    match_percentage = 0

    if required:

        match_percentage = round(
            (len(matched) / len(required)) * 100
        )

    recommendations_list = []

    for skill in missing:

        recommendations_list.append(
            f"Learn {skill} and build a small project using it."
        )

    analysis = models.Analysis(
        resume_id=resume_record.id,
        job_title=job_title,
        match_percentage=match_percentage,
        matched_skills=", ".join(
            sorted(matched)
        ),
        missing_skills=", ".join(
            sorted(missing)
        ),
        recommendations=", ".join(
            recommendations_list
        )
    )

    db.add(analysis)

    db.commit()

    db.refresh(analysis)

    return {
        "analysis_id": analysis.id,
        "resume_id": resume_record.id,
        "job_title": job_title,
        "resume_skills": sorted(resume),
        "match_percentage": match_percentage,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "recommendations": recommendations_list
    }


# =========================================================
# UPLOAD RESUME
# =========================================================

@app.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    current_user: models.User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    upload_folder = "uploads"

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    file_path = os.path.join(
        upload_folder,
        file.filename
    )

    with open(
        file_path,
        "wb"
    ) as buffer:

        buffer.write(
            await file.read()
        )

    reader = PdfReader(
        file_path
    )

    resume_text = ""

    for page in reader.pages:

        text = page.extract_text()

        if text:

            resume_text += (
                text + "\n"
            )

    skills = extract_skills(
        resume_text
    )

    resume_record = models.Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        resume_text=resume_text
    )

    db.add(resume_record)

    db.commit()

    db.refresh(resume_record)

    return {
        "id": resume_record.id,
        "user_id": current_user.id,
        "filename": resume_record.filename,
        "file_path": resume_record.file_path,
        "skills": skills,
        "text_preview": resume_text[:1000]
    }


# =========================================================
# GET USER RESUMES
# =========================================================

@app.get("/resumes")
def get_resumes(
    current_user: models.User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    resumes = (
        db.query(models.Resume)
        .filter(
            models.Resume.user_id == current_user.id
        )
        .all()
    )

    return [

        {
            "id": resume.id,
            "user_id": resume.user_id,
            "filename": resume.filename,
            "file_path": resume.file_path,
            "text_preview": (
                resume.resume_text or ""
            )[:500]
        }

        for resume in resumes
    ]


# =========================================================
# UPLOAD + ANALYZE
# =========================================================

@app.post("/upload-and-analyze")
async def upload_and_analyze(
    file: UploadFile = File(...),
    job_title: str = "",
    current_user: models.User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    required_skills = JOB_ROLES.get(
        job_title
    )

    if required_skills is None:

        return {
            "error": "Job role not found"
        }

    upload_folder = "uploads"

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    file_path = os.path.join(
        upload_folder,
        file.filename
    )

    with open(
        file_path,
        "wb"
    ) as buffer:

        buffer.write(
            await file.read()
        )

    reader = PdfReader(
        file_path
    )

    resume_text = ""

    for page in reader.pages:

        text = page.extract_text()

        if text:

            resume_text += (
                text + "\n"
            )

    resume_skills = extract_skills(
        resume_text
    )

    resume = {
        skill.lower()
        for skill in resume_skills
    }

    required = {
        skill.lower()
        for skill in required_skills
    }

    matched = resume.intersection(
        required
    )

    missing = required - resume

    match_percentage = 0

    if required:

        match_percentage = round(
            (len(matched) / len(required)) * 100
        )

    recommendations_list = []

    for skill in missing:

        recommendations_list.append(
            f"Learn {skill} and build a small project using it."
        )

    resume_record = models.Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        resume_text=resume_text
    )

    db.add(resume_record)

    db.commit()

    db.refresh(resume_record)

    analysis = models.Analysis(
        resume_id=resume_record.id,
        job_title=job_title,
        match_percentage=match_percentage,
        matched_skills=", ".join(
            sorted(matched)
        ),
        missing_skills=", ".join(
            sorted(missing)
        ),
        recommendations=", ".join(
            recommendations_list
        )
    )

    db.add(analysis)

    db.commit()

    db.refresh(analysis)

    return {
        "analysis_id": analysis.id,
        "resume_id": resume_record.id,
        "user_id": current_user.id,
        "filename": file.filename,
        "job_title": job_title,
        "resume_skills": sorted(resume),
        "match_percentage": match_percentage,
        "matched_skills": sorted(matched),
        "missing_skills": sorted(missing),
        "recommendations": recommendations_list
    }