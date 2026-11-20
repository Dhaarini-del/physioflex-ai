"""
PhysioFlex — Machine Learning API Routes
Endpoints for movement quality classification and telemetry analysis.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from ml_service import ml_service

ml_router = APIRouter(prefix="/api/ml", tags=["Machine Learning Movement Analysis"])


class MovementPredictionRequest(BaseModel):
    features: Dict[str, Any] = Field(
        ...,
        description="Dictionary of 144 extracted sensor features."
    )
    patient_id: Optional[str] = None
    exercise_id: Optional[str] = None


@ml_router.get("/health")
async def ml_health():
    """Returns status, loaded model name, accuracy, and feature requirements."""
    return ml_service.get_status_info()


@ml_router.get("/features")
async def ml_features():
    """Returns the ordered list of 144 required sensor features."""
    return {
        "features": ml_service.feature_names,
        "count": len(ml_service.feature_names)
    }


@ml_router.get("/sample")
async def ml_sample():
    """Returns a valid sample sensor input dictionary for testing."""
    return {
        "features": ml_service.get_sample_input()
    }


@ml_router.post("/predict")
async def ml_predict(body: MovementPredictionRequest):
    """Predicts movement execution quality from 144 sensor features."""
    if not ml_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Machine learning model is not available."
        )

    try:
        result = ml_service.predict(body.features)
        if body.patient_id:
            result["patient_id"] = body.patient_id
        if body.exercise_id:
            result["exercise_id"] = body.exercise_id
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")
