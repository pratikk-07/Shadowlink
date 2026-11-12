"""Tests for API file-read safety and directory boundary enforcement.

Verifies that:
- Paths inside SHADOWLINK_DATA_DIR succeed (201).
- Relative paths attempting '../' traversal are rejected (HTTP 400).
- Absolute paths outside the data directory are rejected (HTTP 400).
- Symlinks pointing outside the data directory are rejected (HTTP 400).
- No server file paths are leaked in error responses.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from shadowlink.api.config import settings

SAMPLE_CSV = "age,city\n25,London\n30,Paris\n"


@pytest.fixture
def temp_data_env() -> object:
    """Create an isolated temporary data directory and outside directory."""
    with tempfile.TemporaryDirectory() as base_temp:
        data_dir = Path(base_temp) / "safe_data"
        outside_dir = Path(base_temp) / "outside"
        data_dir.mkdir()
        outside_dir.mkdir()

        safe_csv = data_dir / "safe.csv"
        safe_csv.write_text(SAMPLE_CSV, encoding="utf-8")

        outside_csv = outside_dir / "secret.csv"
        outside_csv.write_text(SAMPLE_CSV, encoding="utf-8")

        old_data_dir = settings.data_dir
        settings.data_dir = str(data_dir)

        yield {
            "data_dir": data_dir,
            "outside_dir": outside_dir,
            "safe_csv": safe_csv,
            "outside_csv": outside_csv,
        }

        settings.data_dir = old_data_dir


def test_inside_dir_relative_ok(
    client: TestClient, temp_data_env: dict[str, Path]
) -> None:
    """A relative path inside SHADOWLINK_DATA_DIR should succeed."""
    resp = client.post("/profile", json={"csv_path": "safe.csv"})
    assert resp.status_code == 201
    assert resp.json()["row_count"] == 2


def test_inside_dir_absolute_ok(
    client: TestClient, temp_data_env: dict[str, Path]
) -> None:
    """An absolute path located inside SHADOWLINK_DATA_DIR should succeed."""
    safe_path = str(temp_data_env["safe_csv"])
    resp = client.post("/profile", json={"csv_path": safe_path})
    assert resp.status_code == 201


def test_dot_dot_traversal_rejected(
    client: TestClient, temp_data_env: dict[str, Path]
) -> None:
    """Path traversal with '../' must be rejected with HTTP 400 and no path leaked."""
    resp = client.post("/profile", json={"csv_path": "../outside/secret.csv"})
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert "Access denied" in detail or "outside" in detail
    assert str(temp_data_env["data_dir"]) not in detail
    assert str(temp_data_env["outside_dir"]) not in detail
    assert "secret.csv" not in detail


def test_absolute_path_outside_rejected(
    client: TestClient, temp_data_env: dict[str, Path]
) -> None:
    """An absolute path outside SHADOWLINK_DATA_DIR must be rejected with HTTP 400."""
    outside_path = str(temp_data_env["outside_csv"])
    resp = client.post("/profile", json={"csv_path": outside_path})
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert outside_path not in detail
    assert "secret.csv" not in detail


def test_risk_path_traversal_rejected(
    client: TestClient, temp_data_env: dict[str, Path]
) -> None:
    """POST /risk must also reject paths outside SHADOWLINK_DATA_DIR."""
    resp = client.post(
        "/risk",
        json={"csv_path": "../outside/secret.csv", "qi_columns": ["age"]},
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert "secret.csv" not in detail


def test_mitigate_path_traversal_rejected(
    client: TestClient, temp_data_env: dict[str, Path]
) -> None:
    """POST /mitigate must also reject paths outside SHADOWLINK_DATA_DIR."""
    resp = client.post(
        "/mitigate",
        json={
            "csv_path": "../outside/secret.csv",
            "qi_columns": ["age"],
            "specs": [
                {
                    "kind": "generalize_age",
                    "parameters": {"column": "age", "bin_width": 5},
                }
            ],
        },
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert "secret.csv" not in detail


def test_symlink_escape_rejected(
    client: TestClient, temp_data_env: dict[str, Path]
) -> None:
    """Symlink inside data_dir pointing outside must be rejected."""
    symlink_path = temp_data_env["data_dir"] / "symlink_escape.csv"
    try:
        os.symlink(temp_data_env["outside_csv"], symlink_path)
    except OSError:
        pytest.skip("Symlink creation requires elevated privileges on Windows")

    resp = client.post("/profile", json={"csv_path": "symlink_escape.csv"})
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert str(temp_data_env["outside_csv"]) not in detail
