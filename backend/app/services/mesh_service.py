from __future__ import annotations

import logging
import struct
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

logger = logging.getLogger("segviewer.mesh")


class MeshService:
    def generate_mesh(
        self, seg_path: str, class_id: int, max_triangles: int = 50000
    ) -> tuple[bytes, dict[str, str]]:
        img = nib.load(seg_path)
        data = np.asarray(img.dataobj)
        spacing = img.header.get_zooms()[:3]

        binary_mask = (data == class_id).astype(np.uint8)

        if binary_mask.sum() == 0:
            return b"", {"X-Mesh-Vertices-Count": "0", "X-Mesh-Faces-Count": "0"}

        voxel_count = binary_mask.sum()
        if voxel_count > 256**3:
            binary_mask = binary_mask[::2, ::2, ::2]
            spacing = tuple(s * 2 for s in spacing)

        vertices, faces = marching_cubes_simple(binary_mask, spacing)

        if len(faces) > max_triangles:
            step = len(faces) // max_triangles
            faces = faces[::step]

        if len(vertices) > 0:
            vertices = laplacian_smooth(vertices, faces, iterations=3)

        vert_bytes = vertices.astype(np.float32).tobytes()
        face_bytes = faces.astype(np.uint32).tobytes()

        headers = {
            "X-Mesh-Vertices-Count": str(len(vertices)),
            "X-Mesh-Faces-Count": str(len(faces)),
            "X-Mesh-Format": "float32-vertices,uint32-faces",
        }

        return vert_bytes + face_bytes, headers


def marching_cubes_simple(
    volume: np.ndarray, spacing: tuple
) -> tuple[np.ndarray, np.ndarray]:
    try:
        from skimage.measure import marching_cubes
        verts, faces, _, _ = marching_cubes(volume, level=0.5, spacing=spacing)
        return verts.astype(np.float32), faces.astype(np.uint32)
    except ImportError:
        logger.warning("scikit-image not available, using fallback mesh generation")
        return _fallback_surface(volume, spacing)


def _fallback_surface(
    volume: np.ndarray, spacing: tuple
) -> tuple[np.ndarray, np.ndarray]:
    coords = np.argwhere(volume > 0).astype(np.float32)
    if len(coords) == 0:
        return np.zeros((0, 3), dtype=np.float32), np.zeros((0, 3), dtype=np.uint32)

    for i in range(3):
        coords[:, i] *= spacing[i]

    max_points = min(len(coords), 10000)
    if len(coords) > max_points:
        indices = np.random.choice(len(coords), max_points, replace=False)
        coords = coords[indices]

    faces = np.zeros((0, 3), dtype=np.uint32)
    return coords, faces


def laplacian_smooth(
    vertices: np.ndarray, faces: np.ndarray, iterations: int = 3, factor: float = 0.5
) -> np.ndarray:
    if len(faces) == 0 or len(vertices) == 0:
        return vertices

    n_verts = len(vertices)
    neighbors: list[set[int]] = [set() for _ in range(n_verts)]

    for face in faces:
        for i in range(3):
            for j in range(3):
                if i != j and face[i] < n_verts and face[j] < n_verts:
                    neighbors[face[i]].add(face[j])

    smoothed = vertices.copy()
    for _ in range(iterations):
        new_verts = smoothed.copy()
        for i in range(n_verts):
            if neighbors[i]:
                neighbor_mean = smoothed[list(neighbors[i])].mean(axis=0)
                new_verts[i] = smoothed[i] + factor * (neighbor_mean - smoothed[i])
        smoothed = new_verts

    return smoothed
