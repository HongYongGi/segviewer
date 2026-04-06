import pytest
from pathlib import Path
import tempfile
import os


@pytest.fixture
def tmp_upload_dir(tmp_path):
    return str(tmp_path / "uploads")


@pytest.fixture
def tmp_results_dir(tmp_path):
    return str(tmp_path / "results")


@pytest.fixture(autouse=True)
def patch_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path / "results"))
    (tmp_path / "uploads").mkdir(exist_ok=True)
    (tmp_path / "results").mkdir(exist_ok=True)
