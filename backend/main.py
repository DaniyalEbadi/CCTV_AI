"""
Main entry point for the backend server.
Initializes FastAPI, detection pipeline, and camera manager.
Serves both REST API and video streaming endpoints.
"""
import logging
import os
import sys
import io
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Dict, Tuple
import cv2
import numpy as np
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse
import uvicorn

from backend.config import get_settings, log_settings
from backend.services import DetectionPipeline, CameraManager
from backend.api import router, set_pipeline, set_camera_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()
logging.getLogger().setLevel(settings.LOG_LEVEL)

# Global services
pipeline: DetectionPipeline = None
camera_manager: CameraManager = None

# Streaming tuning (optimized for CPU-only systems)
NO_FRAME_SLEEP_SEC = float(os.getenv("NO_FRAME_SLEEP_SEC", "0.01"))
MJPEG_QUALITY = int(os.getenv("MJPEG_QUALITY", "75"))
DETECT_STREAM_INTERVAL_SEC = float(os.getenv("DETECT_STREAM_INTERVAL_SEC", "1.0"))
DETECTION_HOLD_SEC = float(os.getenv("DETECTION_HOLD_SEC", "0.7"))

BOX_COLORS: Dict[str, Tuple[int, int, int]] = {
    "person": (60, 220, 60),
    "car": (255, 170, 50),
    "truck": (255, 120, 0),
    "bus": (255, 80, 0),
    "motorcycle": (255, 210, 0),
    "face": (80, 180, 255),
    "motion": (255, 80, 255),
}
DEFAULT_BOX_COLOR: Tuple[int, int, int] = (0, 255, 0)


def _draw_detection_box(frame: np.ndarray, label: str, confidence: float, x1: int, y1: int, x2: int, y2: int) -> None:
    """Draw a readable, high-contrast box and label."""
    h, w = frame.shape[:2]
    thickness = max(2, min(h, w) // 240)
    color = BOX_COLORS.get(label.lower(), DEFAULT_BOX_COLOR)

    # Clamp coords to frame bounds.
    x1 = max(0, min(w - 1, x1))
    y1 = max(0, min(h - 1, y1))
    x2 = max(0, min(w - 1, x2))
    y2 = max(0, min(h - 1, y2))

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)

    text = f"{label} {confidence:.2f}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.45, min(h, w) / 1400)
    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)

    y_text_top = y1 - text_h - baseline - 6
    if y_text_top < 0:
        y_text_top = y1 + 2

    cv2.rectangle(
        frame,
        (x1, y_text_top),
        (x1 + text_w + 8, y_text_top + text_h + baseline + 6),
        color,
        -1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        text,
        (x1 + 4, y_text_top + text_h + 2),
        font,
        font_scale,
        (10, 10, 10),
        max(1, thickness - 1),
        cv2.LINE_AA,
    )


def _has_any_detections(results: Dict[str, object]) -> bool:
    """Return True when at least one detector has at least one detection."""
    for result in results.values():
        detections = getattr(result, "detections", None)
        if detections:
            return True
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager - startup and shutdown."""
    # Startup
    logger.info("=== Backend Starting ===")
    log_settings()

    try:
        # Initialize detection pipeline
        logger.info(f"Initializing detection pipeline with {len(settings.enabled_detectors_list)} detectors...")
        global pipeline
        pipeline = DetectionPipeline(
            device=settings.DEVICE,
            enabled_detectors=settings.enabled_detectors_list,
        )
        pipeline.load_all_models()
        set_pipeline(pipeline)
        logger.info("✓ Detection pipeline ready")

        # Initialize camera manager
        logger.info(f"Initializing camera manager from {settings.GO2RTC_CONFIG}...")
        global camera_manager
        camera_manager = CameraManager(
            settings.GO2RTC_CONFIG,
            rtsp_base_url=settings.go2rtc_rtsp_url,
        )
        set_camera_manager(camera_manager)
        logger.info(f"✓ Camera manager ready with {len(camera_manager.cameras)} cameras")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise

    logger.info("=== Backend Ready ===\n")

    yield

    # Shutdown
    logger.info("=== Backend Shutting Down ===")
    try:
        if pipeline:
            pipeline.unload_all_models()
            logger.info("✓ Detection pipeline unloaded")

        if camera_manager:
            camera_manager.stop_all_cameras()
            logger.info("✓ All cameras stopped")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)

    logger.info("=== Backend Stopped ===")


# Create FastAPI app
app = FastAPI(
    title="go2rtc AI Detection Backend",
    description="AI-powered object detection backend for go2rtc",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)

# Serve static files (HTML dashboard)
template_dir = Path(__file__).parent.parent / "backend" / "template"
if template_dir.exists():
    app.mount("/static", StaticFiles(directory=str(template_dir)), name="static")


@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard."""
    return {
        "service": "go2rtc AI Detection Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "dashboard": "/static/detection_dashboard.html",
    }


@app.get("/dashboard")
async def dashboard():
    """Serve the detection dashboard."""
    dashboard_file = template_dir / "detection_dashboard.html"
    if dashboard_file.exists():
        return StreamingResponse(
            iter([dashboard_file.read_bytes()]),
            media_type="text/html"
        )
    return {"error": "Dashboard not found"}


@app.get("/stream/{camera_name}")
async def stream_camera(camera_name: str):
    """
    Stream camera as Motion JPEG.
    Usage: <img src="/stream/camera_name" alt="Camera Stream">
    """
    if not camera_manager:
        return {"error": "Camera manager not initialized"}

    camera_name = unquote(camera_name)

    # Start camera if not running
    if camera_manager.get_camera_status(camera_name) != "running":
        camera_manager.start_camera(camera_name)

    def frame_generator():
        """Generate frames as MJPEG."""
        while True:
            try:
                frame = camera_manager.get_frame(camera_name)
                if frame is None:
                    time.sleep(NO_FRAME_SLEEP_SEC)
                    continue

                # Encode frame as JPEG
                ret, buffer = cv2.imencode(
                    '.jpg',
                    frame,
                    [cv2.IMWRITE_JPEG_QUALITY, MJPEG_QUALITY],
                )
                if not ret:
                    continue

                # Yield as MJPEG chunk
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n'
                    b'Content-Length: ' + str(len(buffer)).encode() + b'\r\n\r\n'
                    + buffer.tobytes() + b'\r\n'
                )
            except Exception as e:
                logger.error(f"Error streaming camera {camera_name}: {e}")
                break

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/detect-stream/{camera_name}")
async def detect_stream(camera_name: str):
    """
    Stream camera with detection overlays as Motion JPEG.
    Shows bounding boxes in real-time.
    Usage: <img src="/detect-stream/camera_name" alt="Camera with Detections">
    """
    if not pipeline or not camera_manager:
        return {"error": "Services not initialized"}

    camera_name = unquote(camera_name)

    # Start camera if not running
    if camera_manager.get_camera_status(camera_name) != "running":
        camera_manager.start_camera(camera_name)

    def detection_frame_generator():
        """Generate frames with detections as MJPEG."""
        last_results = {}
        last_non_empty_results = {}
        last_non_empty_ts = 0.0
        last_submit_ts = 0.0
        detection_future: Future | None = None
        detection_started_ts = 0.0
        slow_warning_emitted = False
        executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix=f"detect-stream-{camera_name}",
        )

        try:
            while True:
                frame = camera_manager.get_frame(camera_name, auto_start=True)
                if frame is None:
                    time.sleep(NO_FRAME_SLEEP_SEC)
                    continue

                now = time.monotonic()

                # Submit detection work without blocking frame streaming.
                if detection_future is None and now - last_submit_ts >= DETECT_STREAM_INTERVAL_SEC:
                    detection_future = executor.submit(pipeline.run_detections, frame.copy())
                    detection_started_ts = now
                    last_submit_ts = now
                    slow_warning_emitted = False

                if detection_future is not None:
                    if detection_future.done():
                        try:
                            fresh_results = detection_future.result()
                            if _has_any_detections(fresh_results):
                                last_results = fresh_results
                                last_non_empty_results = fresh_results
                                last_non_empty_ts = now
                            else:
                                # Keep previous boxes briefly to reduce flicker on head movement.
                                if last_non_empty_results and now - last_non_empty_ts <= DETECTION_HOLD_SEC:
                                    last_results = last_non_empty_results
                                else:
                                    last_results = fresh_results
                        except Exception as e:
                            logger.error("Detection worker failed | camera=%s err=%s", camera_name, e)
                        finally:
                            detection_future = None
                    elif not slow_warning_emitted and now - detection_started_ts > max(2.0, DETECT_STREAM_INTERVAL_SEC * 2):
                        logger.warning(
                            "Slow detection inference | camera=%s elapsed=%.2fs",
                            camera_name,
                            now - detection_started_ts,
                        )
                        slow_warning_emitted = True

                # Draw detections on frame
                frame_with_boxes = frame.copy()
                for detector_name, detection_result in last_results.items():
                    for detection in detection_result.detections:
                        _draw_detection_box(
                            frame_with_boxes,
                            detection.label,
                            detection.confidence,
                            detection.x1,
                            detection.y1,
                            detection.x2,
                            detection.y2,
                        )

                # Encode frame as JPEG
                ret, buffer = cv2.imencode(
                    '.jpg',
                    frame_with_boxes,
                    [cv2.IMWRITE_JPEG_QUALITY, MJPEG_QUALITY],
                )
                if not ret:
                    continue

                # Yield as MJPEG chunk
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n'
                    b'Content-Length: ' + str(len(buffer)).encode() + b'\r\n\r\n'
                    + buffer.tobytes() + b'\r\n'
                )
        except Exception as e:
            logger.error(f"Error in detection stream {camera_name}: {e}")
        finally:
            if detection_future is not None and not detection_future.done():
                detection_future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

    return StreamingResponse(
        detection_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


def main():
    """Run the backend server."""
    try:
        uvicorn.run(
            app,
            host=settings.HOST,
            port=settings.PORT,
            log_level=settings.LOG_LEVEL.lower(),
        )
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
