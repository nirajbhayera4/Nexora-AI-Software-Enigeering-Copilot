"""FastAPI router: POST /github/architecture"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .github_client import GitHubError
from .service import analyze_repository

router = APIRouter(prefix="/github", tags=["architecture"])


class ArchitectureRequest(BaseModel):
    url: str = Field(..., min_length=1, description="Public GitHub repository URL")


@router.post("/architecture")
def analyze_architecture(body: ArchitectureRequest):
    """Analyse a GitHub repository and return structure, modules, dependency
    graph data, an architecture summary and Mermaid UML diagrams."""
    try:
        return analyze_repository(body.url)
    except GitHubError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)
    except Exception as exc:  # last-resort guard so the API returns JSON
        raise HTTPException(status_code=500, detail="Architecture analysis failed: %s" % exc)
