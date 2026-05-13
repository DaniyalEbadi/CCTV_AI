# Backend Quick Start (Current)

Use this flow to run go2rtc + backend + dashboard with current code.

## 1. Prerequisites
- Python venv with backend dependencies installed.
- FFmpeg installed and accessible.
- go2rtc running with your `go2rtc.yaml`.

## 2. Start go2rtc
From repo root:

```powershell
.\go2rtc.exe -c go2rtc.yaml
```

Check it is up:

```powershell
curl http://127.0.0.1:1984/api/streams
```

## 3. Start Backend API
From repo root:

```powershell
$env:YOLO_CONFIG_DIR = "C:\Users\Dani\Desktop\go2rtc-master\backend\.ultralytics"
python -m backend.main
```

Health check:

```powershell
curl http://127.0.0.1:8000/api/health
```

## 4. Open Dashboard
Recommended (served by backend):
- `http://127.0.0.1:8000/static/detection_dashboard.html`

Optional legacy static server:

```powershell
python backend/template/server.py
```

Then open:
- `http://localhost:8081/detection_dashboard.html`

## 5. Basic API Checks
List cameras:

```powershell
curl http://127.0.0.1:8000/api/cameras
```

Refresh cameras after editing `go2rtc.yaml`:

```powershell
curl -X POST http://127.0.0.1:8000/api/cameras/refresh
```

Start one camera:

```powershell
curl -X POST http://127.0.0.1:8000/api/cameras/DD/start
```

Run one detection request:

```powershell
curl -X POST http://127.0.0.1:8000/api/detect/DD
```

## 6. Detector Control
List detector state:

```powershell
curl http://127.0.0.1:8000/api/detectors
```

Face-only profile (manual API version):

```powershell
curl -X POST http://127.0.0.1:8000/api/detectors/face/enable
curl -X POST http://127.0.0.1:8000/api/detectors/person/disable
curl -X POST http://127.0.0.1:8000/api/detectors/vehicle/disable
curl -X POST http://127.0.0.1:8000/api/detectors/motion/disable
```

Restore default profile:

```powershell
curl -X POST http://127.0.0.1:8000/api/detectors/person/enable
curl -X POST http://127.0.0.1:8000/api/detectors/vehicle/enable
curl -X POST http://127.0.0.1:8000/api/detectors/motion/enable
curl -X POST http://127.0.0.1:8000/api/detectors/face/disable
```

## 7. Key Environment Variables
Common:
- `INFERENCE_DEVICE=cpu|cuda`
- `ENABLED_DETECTORS=person,vehicle,motion`
- `GO2RTC_CONFIG=go2rtc.yaml`
- `GO2RTC_HOST=127.0.0.1`
- `GO2RTC_RTSP_PORT=8554`
- `LOG_LEVEL=INFO`

Performance tuning:
- `YOLO_MODEL_WEIGHTS` (default `yolov8s.pt`)
- `YOLO_IMGSZ` (default `640`)
- `FACE_DETECTOR_BACKEND` (`opencv` default, optional `retinaface`)
- `DETECT_STREAM_INTERVAL_SEC`
- `MJPEG_QUALITY`

## 8. Common Problems
- `No frame yet`: camera started but first decoded frame has not arrived yet.
- `ffmpeg_error` in `/api/detect`: backend FFmpeg failed to decode stream.
- Dashboard black/white page: ensure backend is running and open the `/static/detection_dashboard.html` URL.
- Port bind errors on go2rtc: another process already uses 1984/8554/8555.
