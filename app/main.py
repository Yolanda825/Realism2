"""FastAPI application entry point."""

import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Image Realism Enhancement Engine",
    description="API for analyzing and enhancing perceived realism of images",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build frontend path - go up from app/ to project root, then to frontend/dist
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"

# Serve static files from React build
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")), name="assets")

    @app.get("/", response_class=HTMLResponse)
    async def serve_frontend():
        """Serve the React frontend."""
        index_path = frontend_path / "index.html"
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                return f.read()
        return HTMLResponse(content="<html><body><h1>Frontend not found</h1></body></html>")

# Include API routes (must be after frontend to not override static file handling)
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Initialize storage directory on startup."""
    os.makedirs(settings.storage_path, exist_ok=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
