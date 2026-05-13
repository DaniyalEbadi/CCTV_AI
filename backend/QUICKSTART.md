# Backend Quick Start Guide

## What Changed?

The backend has been completely redesigned with a clean, professional architecture:

### Old Structure (Messy)
```
backend/
├── app.py              # Monolithic mess
├── processor.py        # Corrupted code
├── config.py           # Mixed concerns
└── ... (scattered files)
```

### New Structure (Clean & Modular)
```
backend/
├── core/               # Framework layer
│   ├── base_detector.py        # Abstract interface
│   └── frame_source.py         # Frame acquisition
├── detectors/          # Business logic (pluggable)
│   ├── person/         # Person detection
│   ├── vehicle/        # Vehicle detection
│   ├── face/           # Face detection
│   ├── license_plate/  # License plate + OCR
│   └── motion/         # Motion detection
├── services/           # Orchestration
│   ├── detection_pipeline.py   # Coordinates detectors
│   └── camera_manager.py       # Manages go2rtc streams
├── config/             # Configuration
│   └── settings.py     # Environment variables
├── api/                # REST API
│   └── routes.py       # FastAPI endpoints
└── main.py             # Entry point
```

## Installation

```bash
cd backend
pip install -r requirements.txt
```

### Optional Dependencies

For face detection:
```bash
pip install retina-face
```

For license plate OCR:
```bash
pip install easyocr
```

## Running the Backend

### Start Server
```bash
python -m backend.main
```

Expected output:
```
2026-02-02 15:30:54,290 - __main__ - INFO - === Backend Starting ===
...
2026-02-02 15:30:06,051 - __main__ - INFO - === Backend Ready ===
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Access API
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **Health Check**: http://127.0.0.1:8000/health

## Configuration

Set environment variables before running:

```bash
# Server
export BACKEND_HOST=127.0.0.1
export BACKEND_PORT=8000

# Inference
export INFERENCE_DEVICE=cpu       # "cpu" or "cuda"
export CONFIDENCE_THRESHOLD=0.5

# go2rtc
export GO2RTC_CONFIG=go2rtc.yaml
export GO2RTC_HOST=127.0.0.1
export GO2RTC_PORT=1984

# Detectors to enable (comma-separated)
export ENABLED_DETECTORS=person,vehicle,face,motion

# Logging
export LOG_LEVEL=INFO
```

## Quick Examples

### Test Health
```bash
curl http://127.0.0.1:8000/health
```

### List Cameras
```bash
curl http://127.0.0.1:8000/api/cameras
```

### Start a Camera
```bash
curl -X POST http://127.0.0.1:8000/api/cameras/front_door/start
```

### Run Person Detection
```bash
curl -X POST http://127.0.0.1:8000/api/detect/front_door
```

### Get Only Person Detections
```bash
curl http://127.0.0.1:8000/api/detect/front_door/person
```

### List All Detectors
```bash
curl http://127.0.0.1:8000/api/detectors
```

### Enable/Disable Detectors
```bash
# Enable vehicle detection
curl -X POST http://127.0.0.1:8000/api/detectors/vehicle/enable

# Disable face detection
curl -X POST http://127.0.0.1:8000/api/detectors/face/disable
```

## Key Features

### ✨ Modular Detectors
- Each detector in its own folder with clean interface
- Easy to add new detector types
- Enable/disable detectors at runtime

### ⚡ Performance
- YOLOv8 nano for speed (50-100ms inference on CPU)
- Lightweight motion detection alternative
- Supports GPU acceleration (CUDA)

### 🎯 Clean Architecture
- SOLID principles throughout
- Dependency injection
- Type hints everywhere
- Comprehensive documentation

### 🔗 go2rtc Integration
- Automatically loads cameras from go2rtc.yaml
- Acquires frames via FFmpeg
- Runs detection on live camera streams

### 📊 Production Ready
- Full error handling
- Comprehensive logging
- Configuration management
- FastAPI with CORS support

## Architecture Overview

### Data Flow
```
go2rtc (port 1984)
    ↓
FrameSource (FFmpeg subprocess)
    ↓
DetectionPipeline
    ├─→ PersonDetector (YOLOv8)
    ├─→ VehicleDetector (YOLOv8)
    ├─→ FaceDetector (RetinaFace - optional)
    ├─→ LicensePlateDetector (YOLOv8 + OCR - optional)
    └─→ MotionDetector (Background Subtraction)
    ↓
FastAPI Routes
    ↓
REST API (http://127.0.0.1:8000)
```

### Design Patterns Used

1. **Strategy Pattern**: Each detector is a strategy for different detection tasks
2. **Dependency Injection**: Services injected into API routes
3. **Configuration Management**: Dataclass-based settings with env var support
4. **Service Layer**: Business logic separated from API layer

## Troubleshooting

### Backend won't start
```bash
# Check go2rtc is running
curl http://127.0.0.1:1984/api/streams

# Check go2rtc.yaml path
ls -la go2rtc.yaml

# Check Python version (need 3.9+)
python --version
```

### Face detector disabled
RetinaFace is optional. Install it:
```bash
pip install retina-face
```

### Slow inference
```bash
# Check device
curl http://127.0.0.1:8000/api/settings

# If CPU, disable non-essential detectors
export ENABLED_DETECTORS=person,motion
```

### No cameras loading
```bash
# Verify go2rtc.yaml location and content
cat go2rtc.yaml

# Move to project root if needed
cp /path/to/go2rtc.yaml .
```

## Next Steps

1. Start the backend: `python -m backend.main`
2. Visit Swagger UI: http://127.0.0.1:8000/docs
3. Start a camera: POST `/api/cameras/{name}/start`
4. Run detection: POST `/api/detect/{name}`
5. Check the ARCHITECTURE.md for detailed docs

## Performance Tips

### CPU Optimization
- Disable face/license plate detectors if not needed
- Use motion detection as lightweight alternative
- Process every Nth frame to reduce load

### GPU Optimization
- Set `INFERENCE_DEVICE=cuda`
- Requires NVIDIA GPU + CUDA + torch[cuda]
- Significantly faster inference

### Memory Optimization
- Motion detector uses minimal memory
- Detectors auto-unload on shutdown
- FFmpeg frame queue limited to 1 frame

## Architecture Files

- **ARCHITECTURE.md** - Detailed architecture documentation
- **requirements.txt** - Python dependencies
- **main.py** - Server entry point
- **core/** - Base classes and infrastructure
- **detectors/** - Detection implementations
- **services/** - Business logic orchestration
- **config/** - Configuration management
- **api/** - REST API routes

## For Developers

### Adding a New Detector

1. Create `backend/detectors/mydetector/detector.py`:
```python
from backend.core import BaseDetector, Detection, DetectionResult

class MyDetector(BaseDetector):
    def load_model(self): ...
    def detect(self, frame): ...
    def unload_model(self): ...
```

2. Register in `backend/services/detection_pipeline.py`
3. Update `ENABLED_DETECTORS` environment variable
4. Done! It will automatically appear in API

### Running Tests
```bash
pytest tests/
pytest --cov=backend tests/
```

### Code Style
```bash
# Format code
black backend/

# Type check
mypy backend/

# Lint
flake8 backend/
```

## Support

For detailed architecture information, see: **ARCHITECTURE.md**

For old backend info, see: **backend_old/** (backup of previous version)
