from backend.detectors.face.detector import FaceDetector


def test_face_detector_defaults_to_opencv(monkeypatch):
    monkeypatch.delenv("FACE_DETECTOR_BACKEND", raising=False)

    detector = FaceDetector()

    assert detector.backend == "opencv"


def test_face_detector_respects_retinaface_env(monkeypatch):
    monkeypatch.setenv("FACE_DETECTOR_BACKEND", "retinaface")
    monkeypatch.setattr(
        FaceDetector,
        "_import_retinaface",
        lambda self: setattr(self, "_retinaface_module", object()),
    )

    detector = FaceDetector()

    assert detector.backend == "retinaface"
