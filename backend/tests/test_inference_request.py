"""P0 Pydantic InferenceRequest 모델 테스트."""
import pytest
from pydantic import ValidationError

import sys
sys.path.insert(0, "/data/brave/segviewer/backend")
from app.routers.inference import InferenceRequest


class TestInferenceRequest:
    def test_valid_request(self):
        req = InferenceRequest(
            image_id="550e8400-e29b-41d4-a716-446655440000",
            dataset_id=302,
            full_dataset_name="Dataset302_Segmentation",
        )
        assert req.trainer == "nnUNetTrainer"
        assert req.configuration == "3d_fullres"
        assert req.folds == [0, 1, 2, 3, 4]

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            InferenceRequest(image_id="test")

    def test_missing_image_id(self):
        with pytest.raises(ValidationError):
            InferenceRequest(dataset_id=302, full_dataset_name="Dataset302_Segmentation")

    def test_custom_folds(self):
        req = InferenceRequest(
            image_id="550e8400-e29b-41d4-a716-446655440000",
            dataset_id=302,
            full_dataset_name="Dataset302_Segmentation",
            folds=[0, 1],
        )
        assert req.folds == [0, 1]

    def test_model_dump(self):
        req = InferenceRequest(
            image_id="550e8400-e29b-41d4-a716-446655440000",
            dataset_id=302,
            full_dataset_name="Dataset302_Segmentation",
        )
        d = req.model_dump()
        assert "image_id" in d
        assert "dataset_id" in d
        assert d["dataset_id"] == 302
