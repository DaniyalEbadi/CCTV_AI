# AI Detection Details (Current)

This document explains how AI detection works in the current backend implementation.

## 1. Detection Pipeline

Request path:
1. Client asks for detection (`/api/detect/{camera}`) or opens `/detect-stream/{camera}`.
2. `CameraManager` provides latest decoded frame from `FrameSource`.
3. `DetectionPipeline` runs enabled detectors.
4. Results are returned as JSON or drawn as boxes in MJPEG.

Frame source path:
- Backend reads go2rtc RTSP output (`rtsp://127.0.0.1:8554/<camera>` by default).
- Local FFmpeg decodes to BGR raw frames.
- Only latest frame is kept (multi-consumer safe).

## 2. Active Detectors

Registered detectors:
- `person`
- `vehicle`
- `face`
- `license_plate`
- `motion`

Default enabled set:
- `person,vehicle,motion`

### Person and Vehicle
- Backend uses one shared YOLO inference pass and splits outputs into person/vehicle results.
- Default model: `yolov8s.pt` (configurable with `YOLO_MODEL_WEIGHTS`).

### Face
- Default backend: OpenCV cascades (`FACE_DETECTOR_BACKEND=opencv`).
- Optional: RetinaFace (`FACE_DETECTOR_BACKEND=retinaface`).
- If RetinaFace becomes too slow, code can switch back to OpenCV automatically.

### Motion
- OpenCV background subtraction (fast, CPU-friendly).

### License Plate
- Optional dependency path (EasyOCR). Often disabled by default.

## 3. API Output Model

Successful detection response shape:

```json
{
  "camera": "DD",
  "results": {
    "person": {
      "detections": [
        {
          "label": "person",
          "confidence": 0.88,
          "bbox": {"x1": 12, "y1": 20, "x2": 180, "y2": 300},
          "metadata": {}
        }
      ],
      "inference_time_ms": 280.4,
      "frame_shape": [360, 640, 3]
    }
  },
  "timestamp": "2026-02-19T07:00:00.000000"
}
```

No-frame startup response:

```json
{
  "camera": "DD",
  "detections": {},
  "status": "no_frame_yet",
  "message": "Camera started, frames will be available shortly",
  "timestamp": "2026-02-19T07:00:00.000000"
}
```

FFmpeg failure response:

```json
{
  "camera": "DD",
  "detections": {},
  "status": "ffmpeg_error",
  "message": "...ffmpeg/read error text...",
  "timestamp": "2026-02-19T07:00:00.000000"
}
```

## 4. Dashboard Detection Modes

`detection_dashboard.html` has two modes:
- `Stream`: shows `/stream/{camera}` and polls `/api/detect/{camera}`.
- `Detect`: shows `/detect-stream/{camera}` (boxes are rendered server-side).

Important:
- Face boxes are visible in `Detect` mode, because overlay is generated server-side.
- Face-only toggle uses detector enable/disable API calls.

## 5. Performance Behavior

Current anti-freeze behavior:
- `/api/detect/*` runs model inference in worker thread (`asyncio.to_thread`).
- `/detect-stream/*` runs inference in a dedicated executor and keeps stream output moving.
- Detection result reuse and short hold window reduce overlay flicker.

Main bottlenecks on CPU-only systems:
- Heavy face model backend (RetinaFace) at high frame rates.
- High-resolution source streams (4K main stream).
- Running too many detectors together.

## 6. Recommended Config for Real-Time CPU

- Use camera substream for AI (for example 640x360 or 1280x720).
- Keep defaults unless needed:
  - `ENABLED_DETECTORS=person,vehicle,motion`
  - `FACE_DETECTOR_BACKEND=opencv`
- If face-only is required, enable only face detector.
- Tune:
  - `YOLO_IMGSZ=640`
  - `DETECT_STREAM_INTERVAL_SEC=0.7` to `1.0`
  - `MJPEG_QUALITY=65` to `80`

## 7. Debug Checklist

1. Confirm camera appears in `/api/cameras`.
2. Confirm frame availability with `POST /api/detect/{camera}`.
3. If `no_frame_yet` repeats:
   - check go2rtc stream stability
   - check backend FFmpeg logs
4. If stream is smooth but boxes missing:
   - verify detector enabled state via `/api/detectors`
   - test `Detect` mode (not only `Stream` mode)
5. If face is slow:
   - force `FACE_DETECTOR_BACKEND=opencv`

## 8. Known Limits

- No event history endpoint in backend.
- No WebSocket push channel.
- No automatic cross-camera scheduling.
- Detection quality still depends heavily on source quality and lighting.
