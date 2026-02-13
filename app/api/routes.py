"""API routes for the image realism enhancement service."""

import base64
import uuid
from pathlib import Path
from typing import Dict

import aiofiles
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from pydantic import BaseModel
import time
from fastapi.responses import HTMLResponse
from PIL import Image
import io

from app.config import get_settings
from app.models.schemas import (
    UploadResponse,
    JobResponse,
    JobStatus,
    PipelineResult,
)
from app.pipeline.orchestrator import get_orchestrator

router = APIRouter()

# In-memory job storage (use Redis/DB in production)
jobs: Dict[str, dict] = {}

# Simple in-memory event log for optional frontend tracking
event_logs: list[dict] = []

class EventLog(BaseModel):
    event: str
    data: dict | None = None

settings = get_settings()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "realism-enhancement-engine"}


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """Upload an image for processing."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    content = await file.read()

    if len(content) > settings.max_image_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_image_size // 1024 // 1024}MB."
        )

    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    job_id = str(uuid.uuid4())
    storage_path = Path(settings.storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)

    file_path = storage_path / f"{job_id}.jpg"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "file_path": str(file_path),
        "result": None,
        "error": None,
    }

    return UploadResponse(job_id=job_id, message="Image uploaded successfully")


@router.post("/process/{job_id}", response_model=JobResponse)
async def process_image(job_id: str, background_tasks: BackgroundTasks):
    """Start processing an uploaded image."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] == JobStatus.PROCESSING:
        return JobResponse(job_id=job_id, status=JobStatus.PROCESSING, result=None, error=None)

    if job["status"] == JobStatus.COMPLETED:
        return JobResponse(job_id=job_id, status=JobStatus.COMPLETED, result=job["result"], error=None)

    job["status"] = JobStatus.PROCESSING
    background_tasks.add_task(run_pipeline, job_id)

    return JobResponse(job_id=job_id, status=JobStatus.PROCESSING, result=None, error=None)


async def run_pipeline(job_id: str):
    """Run the enhancement pipeline for a job."""
    job = jobs[job_id]

    try:
        async with aiofiles.open(job["file_path"], "rb") as f:
            image_data = await f.read()

        image_base64 = base64.b64encode(image_data).decode("utf-8")

        orchestrator = get_orchestrator()
        result = await orchestrator.process(image_base64)

        job["status"] = JobStatus.COMPLETED
        job["result"] = result

    except Exception as e:
        job["status"] = JobStatus.FAILED
        job["error"] = str(e)


@router.get("/result/{job_id}", response_model=JobResponse)
async def get_result(job_id: str):
    """Get the result of a processed image."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobResponse(job_id=job_id, status=job["status"], result=job["result"], error=job["error"])


@router.post("/analyze")
async def analyze_image_only(file: UploadFile = File(...)):
    """Analyze an image without enhancement."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    content = await file.read()

    if len(content) > settings.max_image_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_image_size // 1024 // 1024}MB."
        )

    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    image_base64 = base64.b64encode(content).decode("utf-8")

    orchestrator = get_orchestrator()
    result = await orchestrator.analyze_only(image_base64)

    return result


@router.post("/enhance")
async def enhance_image(file: UploadFile = File(...)):
    """Analyze and enhance an image using the expert agent system."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    content = await file.read()

    if len(content) > settings.max_image_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_image_size // 1024 // 1024}MB."
        )

    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    image_base64 = base64.b64encode(content).decode("utf-8")

    orchestrator = get_orchestrator()
    # Simplify path: do not use expert system routing for now; directly run simplified enhancement
    result = await orchestrator.process(image_base64, enhance_image=True, use_expert_system=False)

    return result


@router.post("/track")
async def track_event(event: EventLog):
    """Optional frontend event tracking endpoint (track basic UI interactions)."""
    try:
        event_logs.append({
            "event": event.event,
            "data": event.data or {},
            "ts": time.time(),
        })
    except Exception:
        pass
    return {"status": "ok"}
