"""
FastAPI routes for detection endpoints.
Provides REST API for camera management and detection.
"""
import asyncio
import logging
import time
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
import numpy as np

from backend.config import get_settings
from backend.services import DetectionPipeline, CameraManager

logger = logging.getLogger(__name__)

# Note: Video streaming endpoints are handled in main.py and excluded from Swagger
# This router only handles configuration, health checks, and detection API endpoints
router = APIRouter(prefix="/api", tags=["config"])

# Global instances (initialized in main.py)
pipeline: Optional[DetectionPipeline] = None
camera_manager: Optional[CameraManager] = None
_last_detect_autostart_attempt: Dict[str, float] = {}
AUTO_START_COOLDOWN_SECONDS = 5.0


def set_pipeline(p: DetectionPipeline):
    """Set the detection pipeline instance."""
    global pipeline
    pipeline = p


def set_camera_manager(cm: CameraManager):
    """Set the camera manager instance."""
    global camera_manager
    camera_manager = cm


# Health Check Routes
@router.get("/health", tags=["status"])
async def health_check():
    """
    Health check endpoint.
    
    Returns system status, detectors, and cameras.
    Use this to verify backend is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "detectors": pipeline.get_all_detectors() if pipeline else [],
        "cameras": [c["name"] for c in camera_manager.get_camera_list()] if camera_manager else [],
        "streaming_endpoints": {
            "raw_stream": "/stream/{camera_name}",
            "detection_stream": "/detect-stream/{camera_name}",
            "dashboard": "/static/detection_dashboard.html"
        },
        "api_docs": {
            "swagger": "/docs",
            "redoc": "/redoc"
        }
    }


# Camera Management Routes
@router.get("/cameras", tags=["cameras"])
async def list_cameras():
    """
    List all available cameras from go2rtc.
    
    Returns: List of cameras with status (running, stopped)
    """
    if not camera_manager:
        raise HTTPException(status_code=503, detail="Camera manager not initialized")

    cameras = camera_manager.get_camera_list()
    logger.info("List cameras | total=%d active=%d", len(cameras), len(camera_manager.get_active_cameras()))
    return {
        "cameras": cameras,
        "total": len(cameras),
        "active": len(camera_manager.get_active_cameras()),
    }


@router.post("/cameras/refresh", tags=["cameras"])
async def refresh_cameras():
    """Reload cameras from go2rtc.yaml without restarting backend."""
    if not camera_manager:
        raise HTTPException(status_code=503, detail="Camera manager not initialized")

    summary = camera_manager.reload_config()
    return {
        "status": "refreshed",
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/cameras/{camera_name}/start", tags=["cameras"])
async def start_camera(camera_name: str):
    """Start frame capture for a camera."""
    if not camera_manager:
        raise HTTPException(status_code=503, detail="Camera manager not initialized")

    status = camera_manager.get_camera_status(camera_name)
    if status == "running":
        logger.info("Start camera ignored (already running) | camera=%s", camera_name)
        return {
            "status": "already_running",
            "camera": camera_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

    logger.info("Starting camera | camera=%s", camera_name)
    success = camera_manager.start_camera(camera_name)
    if not success:
        logger.warning("Failed to start camera | camera=%s", camera_name)
        raise HTTPException(status_code=400, detail=f"Failed to start camera {camera_name}")

    return {
        "status": "started",
        "camera": camera_name,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/cameras/{camera_name}/stop", tags=["cameras"])
async def stop_camera(camera_name: str):
    """Stop frame capture for a camera."""
    if not camera_manager:
        raise HTTPException(status_code=503, detail="Camera manager not initialized")

    status = camera_manager.get_camera_status(camera_name)
    if status != "running":
        logger.info("Stop camera ignored (not running) | camera=%s status=%s", camera_name, status)
        return {
            "status": "already_stopped",
            "camera": camera_name,
            "timestamp": datetime.utcnow().isoformat(),
        }

    logger.info("Stopping camera | camera=%s", camera_name)
    success = camera_manager.stop_camera(camera_name)
    if not success:
        logger.warning("Failed to stop camera | camera=%s", camera_name)
        raise HTTPException(status_code=400, detail=f"Failed to stop camera {camera_name}")

    return {
        "status": "stopped",
        "camera": camera_name,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/cameras/{camera_name}/status", tags=["cameras"])
async def camera_status(camera_name: str):
    """Get camera status."""
    if not camera_manager:
        raise HTTPException(status_code=503, detail="Camera manager not initialized")

    status = camera_manager.get_camera_status(camera_name)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_name} not found")

    return {
        "camera": camera_name,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Detection Routes
@router.get("/detectors", tags=["detectors"])
async def list_detectors():
    """List all available detectors."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Detection pipeline not initialized")

    return {
        "detectors": pipeline.get_detector_info(),
        "enabled": pipeline.get_enabled_detectors(),
        "total": len(pipeline.get_all_detectors()),
    }


@router.post("/detectors/{detector_name}/enable", tags=["detectors"])
async def enable_detector(detector_name: str):
    """Enable a specific detector."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Detection pipeline not initialized")

    success = pipeline.enable_detector(detector_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Detector {detector_name} not found")

    return {
        "status": "enabled",
        "detector": detector_name,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/detectors/{detector_name}/disable", tags=["detectors"])
async def disable_detector(detector_name: str):
    """Disable a specific detector."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Detection pipeline not initialized")

    success = pipeline.disable_detector(detector_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Detector {detector_name} not found")

    return {
        "status": "disabled",
        "detector": detector_name,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Detection Inference Routes
@router.post("/detect/{camera_name}", tags=["detection"])
async def detect_objects(camera_name: str):
    """
    Run detection on latest frame from camera.
    
    Args:
        camera_name: Name of camera (URL encoded if contains spaces)
    """
    # URL decode camera name to handle spaces and special characters
    camera_name = unquote(camera_name)
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Detection pipeline not initialized")

    if not camera_manager:
        raise HTTPException(status_code=503, detail="Camera manager not initialized")

    # Validate camera exists
    available_cameras = [c["name"] for c in camera_manager.get_camera_list()]
    if camera_name not in available_cameras:
        logger.warning("Detect request for unknown camera | camera=%s", camera_name)
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{camera_name}' not found. Available: {available_cameras}"
        )

    # Try to get frame WITHOUT auto-starting (non-blocking)
    frame = camera_manager.get_frame(camera_name, auto_start=False)
    
    # If no frame available, start camera in background and return empty result
    if frame is None:
        status_before = camera_manager.get_camera_status(camera_name)
        existing_error = camera_manager.get_last_error(camera_name)
        logger.info("No frame yet | camera=%s status=%s", camera_name, status_before)

        if status_before != "running":
            now = time.monotonic()
            last_attempt = _last_detect_autostart_attempt.get(camera_name, 0.0)
            if now - last_attempt >= AUTO_START_COOLDOWN_SECONDS:
                logger.info("Auto-start camera for detect | camera=%s", camera_name)
                camera_manager.start_camera(camera_name)
                _last_detect_autostart_attempt[camera_name] = now
            else:
                logger.info(
                    "Auto-start on cooldown | camera=%s cooldown=%.1fs",
                    camera_name,
                    AUTO_START_COOLDOWN_SECONDS - (now - last_attempt),
                )

        err = camera_manager.get_last_error(camera_name) or existing_error
        status_after = camera_manager.get_camera_status(camera_name)
        status = "ffmpeg_error" if err else "no_frame_yet"
        if status == "ffmpeg_error":
            msg = err
        elif status_after == "running":
            msg = "Camera running, waiting for first frame"
        else:
            msg = "Camera started, frames will be available shortly"
        return {
            "camera": camera_name,
            "detections": {},
            "status": status,
            "message": msg,
            "timestamp": datetime.utcnow().isoformat(),
        }
    _last_detect_autostart_attempt.pop(camera_name, None)

    # Run CPU-heavy inference off the event loop to avoid stalling streams/API.
    results = await asyncio.to_thread(pipeline.run_detections, frame)
    logger.debug("Detections complete | camera=%s detectors=%d", camera_name, len(results))

    # Format results for JSON response
    formatted_results = {}
    for detector_name, result in results.items():
        formatted_results[detector_name] = {
            "detections": [
                {
                    "label": d.label,
                    "confidence": d.confidence,
                    "bbox": {
                        "x1": d.x1,
                        "y1": d.y1,
                        "x2": d.x2,
                        "y2": d.y2,
                    },
                    "metadata": d.metadata,
                }
                for d in result.detections
            ],
            "inference_time_ms": result.inference_time_ms,
            "frame_shape": result.frame_shape,
        }

    return {
        "camera": camera_name,
        "results": formatted_results,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/detect/{camera_name}/person", tags=["detection"])
async def detect_persons(camera_name: str):
    """
    Detect people in frame from camera.
    
    Args:
        camera_name: Name of camera (URL encoded if contains spaces)
    """
    # URL decode camera name
    camera_name = unquote(camera_name)
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Detection pipeline not initialized")

    if not camera_manager:
        raise HTTPException(status_code=503, detail="Camera manager not initialized")

    # Validate camera exists
    available_cameras = [c["name"] for c in camera_manager.get_camera_list()]
    if camera_name not in available_cameras:
        raise HTTPException(
            status_code=404,
            detail=f"Camera '{camera_name}' not found"
        )

    # Get frame with auto-start
    frame = camera_manager.get_frame(camera_name, auto_start=True)
    if frame is None:
        await asyncio.sleep(0.5)
        frame = camera_manager.get_frame(camera_name, auto_start=False)

    if frame is None:
        raise HTTPException(
            status_code=400,
            detail=f"No frame available from camera '{camera_name}'",
        )

    results = await asyncio.to_thread(pipeline.run_detections, frame)
    person_result = results.get("person")

    if person_result is None:
        raise HTTPException(status_code=400, detail="Person detector not available")

    return {
        "camera": camera_name,
        "detector": "person",
        "detections": [
            {
                "label": d.label,
                "confidence": d.confidence,
                "bbox": {"x1": d.x1, "y1": d.y1, "x2": d.x2, "y2": d.y2},
            }
            for d in person_result.detections
        ],
        "count": len(person_result.detections),
        "inference_time_ms": person_result.inference_time_ms,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Settings Routes
@router.get("/settings", tags=["config"])
async def get_settings_endpoint():
    """Get current settings."""
    settings = get_settings()
    return {
        "device": settings.DEVICE,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "go2rtc_url": settings.go2rtc_api_url,
        "enabled_detectors": settings.enabled_detectors_list,
    }
