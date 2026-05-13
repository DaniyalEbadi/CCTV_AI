"""FastAPI application for AI detection backend."""

import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import AppConfig, get_config, set_config
from .pipeline import DetectionPipeline
from .models import Detection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Data models for API
class HealthResponse(BaseModel):
    status: str
    detectors: list[str]
    config: dict


class DetectionResponse(BaseModel):
    detections: list[dict]
    frame_count: int
    timestamp: float


# Global state
pipeline: DetectionPipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    global pipeline
    
    # Startup
    logger.info("Starting AI detection backend...")
    config = get_config()
    pipeline = DetectionPipeline(config)
    pipeline.initialize()
    logger.info("Backend ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI detection backend...")
    if pipeline:
        pipeline.cleanup()


# Create FastAPI app
app = FastAPI(
    title="AI Detection Backend",
    description="Multi-detector AI system for video analysis",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    config = get_config()
    detectors = list(pipeline.detectors.keys()) if pipeline else []
    
    return HealthResponse(
        status="ok" if pipeline and pipeline._initialized else "initializing",
        detectors=detectors,
        config={
            "yolo_model": config.yolo_model,
            "enable_nms": config.enable_nms,
            "person_confidence": config.person_confidence,
            "vehicle_confidence": config.vehicle_confidence,
            "motion_threshold": config.motion_threshold,
        },
    )


@app.get("/detectors")
async def get_detectors():
    """List available detectors."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    return {
        "detectors": [
            {
                "name": name,
                "enabled": detector.enabled,
                "initialized": detector._initialized,
            }
            for name, detector in pipeline.detectors.items()
        ]
    }


@app.get("/config")
async def get_app_config():
    """Get current configuration."""
    config = get_config()
    return {
        "yolo_model": config.yolo_model,
        "enable_nms": config.enable_nms,
        "person_confidence": config.person_confidence,
        "vehicle_confidence": config.vehicle_confidence,
        "motion_threshold": config.motion_threshold,
        "motion_min_area": config.motion_min_area,
        "max_frame_queue": config.max_frame_queue,
        "frame_skip": config.frame_skip,
    }


@app.post("/config")
async def update_config(config_update: dict):
    """Update configuration."""
    config = get_config()
    
    # Update allowed fields
    allowed_fields = {
        "person_confidence",
        "vehicle_confidence",
        "motion_threshold",
        "motion_min_area",
        "enable_nms",
        "frame_skip",
    }
    
    for key, value in config_update.items():
        if key in allowed_fields and hasattr(config, key):
            setattr(config, key, value)
    
    return {"status": "updated", "config": get_config().__dict__}


@app.on_event("startup")
async def startup_event():
    """Application startup."""
    logger.info("API startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown."""
    logger.info("API shutdown complete")


if __name__ == "__main__":
    import uvicorn
    
    config = get_config()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.api_port,
        log_level="info",
    )
