from backend.detectors.face.detector import FaceDetector


def test_face_dedupe_removes_overlapping_boxes():
    detector = FaceDetector()
    boxes = [
        (100, 100, 80, 80, 0.90),
        (105, 105, 78, 78, 0.82),  # heavy overlap with first box
        (300, 120, 70, 70, 0.88),
    ]

    deduped = detector._dedupe_raw_boxes(boxes)

    assert len(deduped) == 2


def test_face_dedupe_keeps_separate_faces():
    detector = FaceDetector()
    boxes = [
        (100, 100, 80, 80, 0.90),
        (240, 100, 80, 80, 0.86),  # clearly separate
    ]

    deduped = detector._dedupe_raw_boxes(boxes)

    assert len(deduped) == 2


def test_face_plausible_box_filters_invalid_geometry():
    detector = FaceDetector()

    assert detector._is_plausible_face_box(20, 20, 80, 80, frame_w=640, frame_h=360) is True
    assert detector._is_plausible_face_box(20, 20, 300, 40, frame_w=640, frame_h=360) is False
    assert detector._is_plausible_face_box(-1, 20, 80, 80, frame_w=640, frame_h=360) is False
