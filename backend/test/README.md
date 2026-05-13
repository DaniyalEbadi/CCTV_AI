# Backend Testing Guide

This directory contains comprehensive tests for the go2rtc backend AI detection system. Tests are organized into four categories following best practices for test organization.

## Test Structure

```
backend/test/
├── conftest.py                 # Shared pytest fixtures and configuration
├── pytest.ini                  # Pytest configuration
├── requirements-test.txt       # Testing dependencies
├── README.md                   # This file
│
├── unit/                       # Unit tests - test individual components in isolation
│   ├── test_models_detection.py       # Detection model tests
│   ├── test_config.py                 # Configuration tests
│   ├── test_base_detector.py          # Base detector interface tests
│   └── test_motion_detector.py        # Motion detector tests
│
├── integration/                # Integration tests - test component interactions
│   ├── test_camera_manager.py         # Camera manager integration tests
│   └── test_detection_pipeline.py     # Detection pipeline integration tests
│
├── security/                   # Security tests - test input validation and injection prevention
│   └── test_input_validation.py       # Input validation and security tests
│
└── end_2_end/                  # End-to-end tests - test complete workflows
    ├── test_api_endpoints.py          # API endpoint tests
    └── test_detection_workflow.py     # Complete detection workflow tests
```

## Test Categories

### Unit Tests (`unit/`)
Test individual components in isolation with mocked dependencies.

**Files:**
- `test_models_detection.py` - Tests for Detection, BoundingBox, and DetectionResult models
- `test_config.py` - Tests for configuration loading and validation
- `test_base_detector.py` - Tests for BaseDetector abstract class
- `test_motion_detector.py` - Tests for MotionDetector implementation

**Run unit tests:**
```bash
pytest backend/test/unit/ -v
```

### Integration Tests (`integration/`)
Test interactions between multiple components.

**Files:**
- `test_camera_manager.py` - Tests for CameraManager with go2rtc integration
- `test_detection_pipeline.py` - Tests for DetectionPipeline orchestration

**Run integration tests:**
```bash
pytest backend/test/integration/ -v
```

### Security Tests (`security/`)
Test input validation, injection prevention, and security boundaries.

**Files:**
- `test_input_validation.py` - Tests for configuration validation, detector input validation, and injection prevention

**Run security tests:**
```bash
pytest backend/test/security/ -v
```

### End-to-End Tests (`end_2_end/`)
Test complete workflows from HTTP request to detection results.

**Files:**
- `test_api_endpoints.py` - Tests for all API endpoints (health, cameras, detectors, detection)
- `test_detection_workflow.py` - Tests for complete detection workflows

**Run end-to-end tests:**
```bash
pytest backend/test/end_2_end/ -v
```

## Running Tests

### Run all tests
```bash
pytest backend/test/ -v
```

### Run specific test category
```bash
pytest backend/test/unit/ -v          # Unit tests only
pytest backend/test/integration/ -v   # Integration tests only
pytest backend/test/security/ -v      # Security tests only
pytest backend/test/end_2_end/ -v     # End-to-end tests only
```

### Run specific test file
```bash
pytest backend/test/unit/test_config.py -v
```

### Run specific test class
```bash
pytest backend/test/unit/test_config.py::TestAppConfig -v
```

### Run specific test function
```bash
pytest backend/test/unit/test_config.py::TestAppConfig::test_config_default_values -v
```

### Run with coverage report
```bash
pytest backend/test/ --cov=backend --cov-report=html
```

### Run with markers
```bash
pytest backend/test/ -m unit              # Run only unit tests
pytest backend/test/ -m integration       # Run only integration tests
pytest backend/test/ -m security          # Run only security tests
pytest backend/test/ -m end_2_end         # Run only end-to-end tests
```

## Test Coverage

Current test coverage includes:

### Models
- ✅ Detection model with bounding box calculations
- ✅ BoundingBox IoU (Intersection over Union) calculations
- ✅ Detection serialization to JSON
- ✅ DetectionResult aggregation

### Configuration
- ✅ Configuration loading from environment variables
- ✅ Configuration validation (port, FPS, confidence, backend)
- ✅ Global configuration singleton pattern
- ✅ Configuration isolation

### Detectors
- ✅ BaseDetector abstract interface
- ✅ Detector initialization and lifecycle
- ✅ Context manager support
- ✅ Motion detector with background subtraction
- ✅ Detector enable/disable functionality
- ✅ Confidence threshold handling

### Camera Manager
- ✅ Camera configuration loading from go2rtc.yaml
- ✅ Camera start/stop operations
- ✅ Frame retrieval from cameras
- ✅ Multiple camera management
- ✅ Error handling for missing cameras
- ✅ Custom stream URL support

### Detection Pipeline
- ✅ Pipeline initialization with detector selection
- ✅ Detector orchestration and result aggregation
- ✅ Enable/disable individual detectors
- ✅ Model loading and unloading
- ✅ Error handling in detector failures

### API Endpoints
- ✅ Health check endpoint
- ✅ Camera listing and status
- ✅ Camera start/stop operations
- ✅ Detector listing and control
- ✅ Detection inference endpoints
- ✅ Settings endpoint

### Security
- ✅ Configuration validation and bounds checking
- ✅ Input validation for detector parameters
- ✅ Path traversal prevention
- ✅ SQL injection prevention
- ✅ Detector name validation
- ✅ Frame input validation

### Workflows
- ✅ Complete detection pipeline workflow
- ✅ Camera to detection workflow
- ✅ Multiple frame sequential processing
- ✅ Detector enable/disable during operation
- ✅ Different frame size handling
- ✅ Error handling and recovery

## Test Fixtures

Common fixtures available in `conftest.py`:

```python
@pytest.fixture
def sample_frame():
    """Create a sample BGR frame (480x640x3)."""
    
@pytest.fixture
def sample_frame_large():
    """Create a larger sample BGR frame (1080x1920x3)."""
    
@pytest.fixture
def sample_frame_small():
    """Create a small sample BGR frame (240x320x3)."""
    
@pytest.fixture
def mock_camera_manager():
    """Create a mock camera manager."""
    
@pytest.fixture
def mock_detection_pipeline():
    """Create a mock detection pipeline."""
    
@pytest.fixture
def test_config():
    """Create a test configuration."""
    
@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary storage directory."""
```

## Writing New Tests

### Unit Test Template
```python
class TestMyComponent:
    """Test MyComponent class."""
    
    def test_initialization(self):
        """Test component initialization."""
        component = MyComponent()
        assert component.property == expected_value
    
    def test_functionality(self):
        """Test component functionality."""
        component = MyComponent()
        result = component.method()
        assert result == expected_result
```

### Integration Test Template
```python
@patch("module.Dependency")
def test_integration(mock_dependency):
    """Test component integration."""
    mock_instance = MagicMock()
    mock_dependency.return_value = mock_instance
    
    component = MyComponent()
    result = component.method()
    
    assert result == expected_result
    mock_instance.method.assert_called_once()
```

### Security Test Template
```python
def test_input_validation(self):
    """Test input validation."""
    with pytest.raises(ValueError):
        component = MyComponent(invalid_input="bad")
```

## Best Practices

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Clear Names**: Test names should clearly describe what is being tested
3. **Arrange-Act-Assert**: Follow the AAA pattern in test structure
4. **Mock External Dependencies**: Use mocks for external services and I/O
5. **Test Edge Cases**: Include tests for boundary conditions and error cases
6. **Meaningful Assertions**: Use specific assertions with clear error messages
7. **DRY Principle**: Use fixtures to avoid code duplication
8. **Documentation**: Add docstrings to test classes and functions

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```bash
# Install test dependencies
pip install -r backend/test/requirements-test.txt

# Run all tests with coverage
pytest backend/test/ --cov=backend --cov-report=xml

# Run specific test category
pytest backend/test/unit/ -v
```

## Troubleshooting

### Import Errors
Ensure the backend module is in PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest backend/test/
```

### Mock Issues
Use `patch` decorator or context manager for mocking:
```python
from unittest.mock import patch, MagicMock

@patch("module.Class")
def test_something(mock_class):
    mock_instance = MagicMock()
    mock_class.return_value = mock_instance
```

### Async Test Issues
Use `pytest-asyncio` for async tests:
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure tests pass locally
3. Maintain or improve code coverage
4. Follow existing test patterns
5. Update this README if adding new test categories

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
