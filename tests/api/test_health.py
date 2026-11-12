"""Tests for GET /health."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_body(client: TestClient) -> None:
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["version"] == "0.1.0"

