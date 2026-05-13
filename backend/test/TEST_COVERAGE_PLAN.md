# Backend Test Suite - Comprehensive Testing Strategy

## Overview

Comprehensive test coverage for the entire AI detection backend across 4 testing layers:

1. **Unit Tests** - Test individual components in isolation
2. **Integration Tests** - Test components working together
3. **Security Tests** - Test input validation, injection prevention, auth
4. **End-to-End Tests** - Test complete workflows and API endpoints

---

## Test Structure

```
backend/test/
├── unit/                          # Individual component tests
│   ├── test_base_detector.py       # Test BaseDetector interface
│   ├── test_motion_detector.py     # Test motion detection algorithm
│   ├── test_models_detection.py    # Test Detection/DetectionResult models
│   ├── test_config.py              # Test configuration management
│   └── test_frame_source.py        # Test frame acquisition
│
├── integration/                   # Component interaction tests
│   ├── test_detection_pipeline.py  # Test detector orchestration
│   ├── test_camera_manager.py      # Test camera/stream management
│   ├── test_detectors_person.py    # Test person detector integration
│   ├── test_detectors_vehicle.py   # Test vehicle detector integration
│   └── test_detectors_motion.py    # Test motion detector integration
│
├── security/                      # Security and input validation tests
│   ├── test_input_validation.py    # Test API input validation
│   ├── test_injection_prevention.py # Test injection/XSS prevention
│   ├── test_rate_limiting.py       # Test rate limiting
│   └── test_error_handling.py      # Test error handling
│
├── end_2_end/                     # Full workflow tests
│   ├── test_api_endpoints.py       # Test all REST endpoints
│   ├── test_detection_workflow.py  # Test full detection flow
│   ├── test_camera_workflow.py     # Test camera management flow
│   └── test_error_scenarios.py     # Test error handling flows
│
├── pytest.ini                     # pytest configuration
├── requirements-test.txt          # Test dependencies
└── README.md                       # Testing guide

```

---

## Testing Framework

- **Framework**: pytest
- **Mocking**: pytest-mock, unittest.mock
- **Async**: pytest-asyncio
- **Coverage**: pytest-cov
- **Fixtures**: pytest fixtures for reusable test setup

---

## Test Categories

### Unit Tests (Fast, Isolated)

**Purpose**: Test individual functions and classes in isolation

**Coverage**:
- ✅ BaseDetector abstract class
- ✅ Motion detection algorithm
- ✅ Detection/DetectionResult data models
- ✅ Configuration settings loading
- ✅ Frame source frame reading

**Example**:
```python
def test_motion_detector_initialization():
    """Test MotionDetector initializes correctly"""
    detector = MotionDetector(confidence_threshold=0.7)
    assert detector.name == "motion_detector"
    assert detector.enabled == True
    assert detector.confidence_threshold == 0.7
```

### Integration Tests (Medium Speed, Interactive)

**Purpose**: Test multiple components working together

**Coverage**:
- ✅ DetectionPipeline with all detectors
- ✅ CameraManager with FrameSource
- ✅ Person detector with frames
- ✅ Vehicle detector with frames
- ✅ Motion detector with frames

**Example**:
```python
async def test_detection_pipeline_person_detection(sample_frame):
    """Test DetectionPipeline runs person detection"""
    pipeline = DetectionPipeline(device="cpu", enabled_detectors=["person"])
    pipeline.load_all_models()
    
    results = pipeline.run_detections(sample_frame)
    
    assert "person" in results
    assert isinstance(results["person"], DetectionResult)
    pipeline.unload_all_models()
```

### Security Tests (Medium Speed, Validation Focus)

**Purpose**: Test security, input validation, error handling

**Coverage**:
- ✅ Invalid camera names (injection attempts)
- ✅ Invalid confidence thresholds
- ✅ Null/empty inputs
- ✅ Special characters in names
- ✅ Very large inputs
- ✅ Rate limiting checks
- ✅ Error message disclosure

**Example**:
```python
@pytest.mark.asyncio
async def test_detect_endpoint_invalid_camera_name():
    """Test detect endpoint rejects invalid camera names"""
    response = await client.post(f"/api/detect/'; DROP TABLE cameras; --")
    assert response.status_code == 404
    # Ensure no SQL injection occurred
    assert "DROP TABLE" not in response.json()["detail"]
```

### End-to-End Tests (Slower, Full Workflows)

**Purpose**: Test complete user workflows and API flows

**Coverage**:
- ✅ List cameras endpoint
- ✅ Start camera endpoint
- ✅ Stop camera endpoint
- ✅ Detect objects endpoint
- ✅ Person detection endpoint
- ✅ Enable/disable detectors
- ✅ Health check endpoint
- ✅ Settings endpoint
- ✅ Camera with spaces in name
- ✅ Error recovery workflows

**Example**:
```python
@pytest.mark.asyncio
async def test_full_detection_workflow():
    """Test complete detection workflow"""
    # 1. Start camera
    response = await client.post(f"/api/cameras/front_door/start")
    assert response.status_code == 200
    
    # 2. Wait for frame
    await asyncio.sleep(1)
    
    # 3. Run detection
    response = await client.post(f"/api/detect/front_door")
    assert response.status_code == 200
    
    data = response.json()
    assert "results" in data
    assert "person" in data["results"]
    
    # 4. Stop camera
    response = await client.post(f"/api/cameras/front_door/stop")
    assert response.status_code == 200
```

---

## Test Data & Fixtures

### Sample Test Frames

```python
@pytest.fixture
def sample_frame():
    """Generate a sample test frame (480x640x3 BGR)"""
    return np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

@pytest.fixture
def sample_frame_with_person():
    """Generate a frame with simulated person detection"""
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
    # Draw a bounding box area
    frame[100:200, 150:250] = 200
    return frame
```

### Mock Dependencies

```python
@pytest.fixture
def mock_camera_manager(mocker):
    """Mock CameraManager for testing"""
    return mocker.MagicMock()

@pytest.fixture
def mock_detection_pipeline(mocker):
    """Mock DetectionPipeline for testing"""
    return mocker.MagicMock()
```

---

## Running Tests

### Run all tests:
```bash
pytest backend/test/ -v
```

### Run specific layer:
```bash
pytest backend/test/unit/ -v                 # Unit tests
pytest backend/test/integration/ -v          # Integration tests
pytest backend/test/security/ -v             # Security tests
pytest backend/test/end_2_end/ -v            # E2E tests
```

### Run with coverage:
```bash
pytest backend/test/ --cov=backend --cov-report=html
```

### Run specific test:
```bash
pytest backend/test/unit/test_motion_detector.py::test_motion_detector_initialization -v
```

### Run tests in parallel:
```bash
pytest backend/test/ -n auto
```

---

## Coverage Goals

- **Unit Tests**: 90%+ coverage of core logic
- **Integration Tests**: 80%+ coverage of service interactions
- **Security Tests**: 100% coverage of API inputs
- **E2E Tests**: All user workflows covered

**Current Target**: 85%+ overall coverage

---

## Test Dependencies

```
pytest==7.4.0
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.11.1
pytest-xdist==3.3.1
numpy==1.26.3
opencv-python==4.8.1.78
fastapi==0.104.1
httpx==0.24.1
```

---

## Continuous Integration

**Trigger**: On every commit
**Steps**:
1. Run unit tests (fast)
2. Run integration tests (medium)
3. Run security tests (validation)
4. Run E2E tests (slow)
5. Generate coverage report
6. Block PR if coverage < 80%

---

## Next Steps

1. ✅ Create test fixtures and mocks
2. ✅ Implement unit tests (fast feedback)
3. ✅ Implement integration tests (detector validation)
4. ✅ Implement security tests (input validation)
5. ✅ Implement E2E tests (workflow validation)
6. ✅ Set up CI/CD pipeline
7. ✅ Monitor coverage trends

