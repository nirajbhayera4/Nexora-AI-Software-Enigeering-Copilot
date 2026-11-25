from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.github import router as github_router

app = FastAPI(
    title="Nexora - AI Software Engineering Copilot",
    description="AI-powered software engineering assistant",
    version="1.0.0"
)

# CORS configuration
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

# GitHub routes
app.include_router(github_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to Nexora - AI Software Engineering Copilot",
        "status": "success"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }