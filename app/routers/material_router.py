"""
Talyn Material Router — document analysis and schedule generation.

Two endpoints, two prices:
  POST /coach/analyze-material   → free preview (topics, objectives, duration)
  POST /coach/generate-schedule  → the paid day-by-day plan

Both take extracted plain text, never raw files: parsing lives in the
backend, language lives here.
"""

from fastapi import APIRouter, HTTPException
from app.backend_client import BackendError, resolve_learner
from app.models.schemas import (
    AnalyzeMaterialRequest,
    GenerateScheduleRequest,
    MaterialAnalysisResponse,
    StudyScheduleResponse,
)
from app.services import material_service

router = APIRouter(prefix="/coach", tags=["Study Materials"])


@router.post(
    "/analyze-material",
    response_model=MaterialAnalysisResponse,
    summary="Describe a study document: topics, objectives, study time",
)
async def analyze_material(body: AnalyzeMaterialRequest):
    """
    The free preview behind "Here's what we found". One call per analysis —
    the backend decides when re-analysis is warranted, not the caller.
    """
    try:
        resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return material_service.analyze_material(
            body.document_text, body.filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/generate-schedule",
    response_model=StudyScheduleResponse,
    summary="Build the paid day-by-day study schedule from a document",
)
async def generate_schedule(body: GenerateScheduleRequest):
    """
    Runs only after the backend has confirmed payment. The backend stores
    the result; this endpoint is pure generation with no side effects.
    """
    try:
        resolve_learner(body.learner, body.backend_token)
    except BackendError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    try:
        return material_service.generate_schedule(
            body.document_text,
            body.topics,
            body.objectives,
            body.days,
            body.difficulty,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
