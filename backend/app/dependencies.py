"""FastAPI dependency injection for services."""
from __future__ import annotations

from functools import lru_cache

from app.services.image_service import ImageService
from app.services.inference_service import InferenceService
from app.services.mesh_service import MeshService
from app.services.model_service import ModelService
from app.services.segment_service import SegmentService


@lru_cache
def get_image_service() -> ImageService:
    return ImageService()


@lru_cache
def get_inference_service() -> InferenceService:
    return InferenceService()


@lru_cache
def get_model_service() -> ModelService:
    return ModelService()


@lru_cache
def get_segment_service() -> SegmentService:
    return SegmentService()


@lru_cache
def get_mesh_service() -> MeshService:
    return MeshService()
