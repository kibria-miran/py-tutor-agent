import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path, monkeypatch):
    """Keep every test away from the real progress file and sandbox."""
    monkeypatch.setattr(config, "PROGRESS_PATH", tmp_path / "progress.json")
    monkeypatch.setattr(config, "SANDBOX_DIR", tmp_path / "sandbox")
    monkeypatch.setattr(config, "LOG_PATH", tmp_path / "logs" / "tutor.log")
    monkeypatch.setattr(config, "RUN_TIMEOUT", 10)
    monkeypatch.setattr(config, "PASS_RATIO", 0.6)
    yield
