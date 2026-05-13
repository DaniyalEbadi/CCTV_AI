from backend.services.detection_pipeline import DetectionPipeline


def test_pipeline_keeps_all_detectors_registered_for_runtime_toggle():
    pipeline = DetectionPipeline(
        device="cpu",
        enabled_detectors=["person", "vehicle", "motion"],
    )

    assert "person" in pipeline.detectors
    assert "vehicle" in pipeline.detectors
    assert "motion" in pipeline.detectors
    assert "face" in pipeline.detectors
    assert "license_plate" in pipeline.detectors

    assert pipeline.detectors["person"].enabled is True
    assert pipeline.detectors["vehicle"].enabled is True
    assert pipeline.detectors["motion"].enabled is True
    assert pipeline.detectors["face"].enabled is False
    assert pipeline.detectors["license_plate"].enabled is False
