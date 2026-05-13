# Backend Architecture (Current - Feb 2026)

This document describes the backend exactly as it runs now.

## 1. Runtime Model
- Request-driven system.
- No background AI worker pipeline for all cameras.
- A camera FFmpeg process starts only when needed (`/stream`, `/detect-stream`, or `/api/detect`).
- Detection results are returned either as JSON (`/api/detect/*`) or rendered into MJPEG (`/detect-stream/*`).

## 2. End-to-End Data Path
1. `CameraManager` reads `go2rtc.yaml` and builds camera entries.
2. For each active camera, `FrameSource` runs local FFmpeg against `rtsp://<go2rtc-host>:8554/<camera>`.
3. FFmpeg decodes video to raw BGR frames (`rawvideo`, `bgr24`) and keeps a latest-frame buffer.
4. `DetectionPipeline` runs enabled detectors on that latest frame.
5. API returns JSON or a rendered MJPEG stream with boxes.

## 3. Main Components
- `backend/main.py`
  - FastAPI app startup/shutdown.
  - Static dashboard mount at `/static`.
  - MJPEG endpoints: `/stream/{camera}` and `/detect-stream/{camera}`.
- `backend/api/routes.py`
  - `/api/*` endpoints for health, cameras, detector toggles, and detection.
  - Detection runs in `asyncio.to_thread(...)` to avoid blocking the event loop.
- `backend/services/camera_manager.py`
  - Parses `go2rtc.yaml`.
  - Starts/stops one `FrameSource` per camera.
  - Supports live reload via `POST /api/cameras/refresh`.
- `backend/core/frame_source.py`
  - Owns FFmpeg subprocess and frame reader thread.
  - Stores only the latest frame under lock (multi-consumer safe).
  - Captures FFmpeg stderr tail for useful error reporting.
- `backend/services/detection_pipeline.py`
  - Registers all detectors up front.
  - Enables/disables detectors at runtime.
  - Uses one shared YOLO pass for person + vehicle to reduce CPU load.

## 4. Detector Stack (Current)
- `person` (YOLO via Ultralytics)
- `vehicle` (YOLO via Ultralytics, vehicle class filter)
- `motion` (OpenCV background subtraction)
- `face` (OpenCV cascades by default; optional RetinaFace)
- `license_plate` (optional; depends on EasyOCR)

Notes:
- Default enabled detectors are: `person,vehicle,motion`.
- Face and license plate are available but disabled by default.

## 5. Streaming Behavior
- `/stream/{camera}`
  - Raw MJPEG from latest decoded frame.
- `/detect-stream/{camera}`
  - MJPEG with overlays.
  - Detection runs on a background worker (`ThreadPoolExecutor`) so stream rendering stays responsive.
  - Reuses latest detections between inference runs.

## 6. API Behavior Details
- `POST /api/detect/{camera}`
  - If no frame exists yet:
    - Starts camera once (cooldown-protected).
    - Returns `status: no_frame_yet`.
    - Returns `status: ffmpeg_error` when FFmpeg startup/read failed and error text is available.
- `POST /api/detectors/{name}/enable|disable`
  - Toggle detectors live without server restart.
- `POST /api/cameras/refresh`
  - Re-reads `go2rtc.yaml` and updates camera list.

## 7. Configuration In Use
From `backend/config/settings.py`:
- `BACKEND_HOST` (default `127.0.0.1`)
- `BACKEND_PORT` (default `8000`)
- `INFERENCE_DEVICE` (`cpu` or `cuda`)
- `CONFIDENCE_THRESHOLD`
- `GO2RTC_CONFIG`
- `GO2RTC_HOST`
- `GO2RTC_PORT`
- `GO2RTC_RTSP_PORT`
- `ENABLED_DETECTORS` (default `person,vehicle,motion`)
- `LOG_LEVEL`

Additional runtime tuning used by current code:
- `YOLO_MODEL_WEIGHTS` (default `yolov8s.pt`)
- `YOLO_IMGSZ` (default `640`)
- `YOLO_IOU` (default `0.45`)
- `FACE_DETECTOR_BACKEND` (`opencv` default, optional `retinaface`)
- `MJPEG_QUALITY`, `DETECT_STREAM_INTERVAL_SEC`, `DETECTION_HOLD_SEC`, `NO_FRAME_SLEEP_SEC`

## 8. What Is Not Implemented
- No WebSocket event bus.
- No persistent AI event history endpoint.
- No built-in recording/retention pipeline in backend.
- No always-on multi-camera AI scheduler.

## 9. go2rtc Relationship
- go2rtc is the stream gateway/transcoder.
- Backend consumes go2rtc RTSP output and performs its own frame decode with local FFmpeg.
- Recommended pattern:
  - Keep a stable stream in go2rtc (`h264 substream` or `ffmpeg:...#video=h264`).
  - Let backend read from `rtsp://127.0.0.1:8554/<stream_name>`.
