"""Repository Architecture Analysis (Member 2).

Usage in backend/app/main.py:

    from app.architecture import router as architecture_router
    app.include_router(architecture_router)
"""
from .router import router

__all__ = ["router"]
