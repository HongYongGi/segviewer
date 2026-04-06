from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger("segviewer.model")

DATASET_PATTERN = re.compile(r"^Dataset(\d{3,4})_(.+)$")
CONFIG_PATTERN = re.compile(r"^(.+?)__(.+?)__(.+)$")
FOLD_PATTERN = re.compile(r"^fold_(\d+)$")


class ModelService:
    def __init__(self) -> None:
        self._cache: list[dict[str, Any]] = []
        self._scanned_at: str | None = None

    def scan(self) -> list[dict[str, Any]]:
        path = settings.nnunet_results_path
        if not path:
            logger.warning("nnunet_results_path not configured")
            self._cache = []
            return []

        root = Path(path)
        if not root.exists():
            logger.warning("nnUNet_results path not found: %s", root)
            self._cache = []
            return []

        models: list[dict[str, Any]] = []
        for dataset_dir in sorted(root.iterdir()):
            if not dataset_dir.is_dir():
                continue
            m = DATASET_PATTERN.match(dataset_dir.name)
            if not m:
                continue

            dataset_id = m.group(1)
            dataset_name = m.group(2)
            configurations = self._scan_configurations(dataset_dir)
            if configurations:
                models.append({
                    "dataset_id": dataset_id,
                    "dataset_name": dataset_name,
                    "full_dataset_name": dataset_dir.name,
                    "configurations": configurations,
                })

        self._cache = models
        self._scanned_at = datetime.now(timezone.utc).isoformat()
        logger.info("Scanned %d models from %s", len(models), root)
        return models

    def get_models(self) -> dict[str, Any]:
        if not self._cache and settings.nnunet_results_path:
            self.scan()
        return {
            "models": self._cache,
            "nnunet_results_path": settings.nnunet_results_path or "",
            "scanned_at": self._scanned_at,
        }

    def refresh(self) -> dict[str, Any]:
        self.scan()
        return {
            "message": "모델 목록을 다시 스캔했습니다.",
            "model_count": sum(
                len(m["configurations"]) for m in self._cache
            ),
            "scanned_at": self._scanned_at,
        }

    def _scan_configurations(self, dataset_dir: Path) -> list[dict[str, Any]]:
        configs = []
        for config_dir in sorted(dataset_dir.iterdir()):
            if not config_dir.is_dir():
                continue
            m = CONFIG_PATTERN.match(config_dir.name)
            if not m:
                continue

            trainer, plans, configuration = m.group(1), m.group(2), m.group(3)
            folds = self._scan_folds(config_dir)
            labels = self._extract_labels(config_dir)
            has_pp = (config_dir / "postprocessing.json").exists()

            if not folds:
                continue

            configs.append({
                "trainer": trainer,
                "plans": plans,
                "configuration": configuration,
                "available_folds": folds,
                "has_postprocessing": has_pp,
                "labels": labels,
                "num_classes": len(labels),
                "checkpoint_type": "best",
            })
        return configs

    def _scan_folds(self, config_dir: Path) -> list[int]:
        folds = []
        for d in sorted(config_dir.iterdir()):
            if not d.is_dir():
                continue
            m = FOLD_PATTERN.match(d.name)
            if not m:
                continue
            fold_num = int(m.group(1))
            has_ckpt = (
                (d / "checkpoint_best.pth").exists()
                or (d / "checkpoint_final.pth").exists()
            )
            if has_ckpt:
                folds.append(fold_num)
        return folds

    def _extract_labels(self, config_dir: Path) -> dict[str, int]:
        dataset_json = config_dir / "dataset.json"
        if not dataset_json.exists():
            return {"background": 0}
        try:
            data = json.loads(dataset_json.read_text())
            return data.get("labels", {"background": 0})
        except Exception:
            logger.warning("Failed to parse dataset.json: %s", dataset_json)
            return {"background": 0}
