"""Tests for bound pagination on all list endpoints.

Verifies that on /profile, /risk, and /mitigate:
- limit must be between 1 and 200 (ge=1, le=200). Values < 1 or > 200 return HTTP 422.
- offset must be >= 0 (ge=0). Values < 0 return HTTP 422.
- Valid values (limit=1, limit=200, offset=0, offset=5) return HTTP 200.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

ENDPOINTS = ["/profile", "/risk", "/mitigate"]


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_pagination_defaults_return_200(client: TestClient, endpoint: str) -> None:
    resp = client.get(endpoint)
    assert resp.status_code == 200


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_pagination_valid_bounds_return_200(client: TestClient, endpoint: str) -> None:
    resp = client.get(f"{endpoint}?limit=1&offset=0")
    assert resp.status_code == 200

    resp = client.get(f"{endpoint}?limit=200&offset=10")
    assert resp.status_code == 200


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_pagination_limit_below_minimum_returns_422(
    client: TestClient, endpoint: str
) -> None:
    resp = client.get(f"{endpoint}?limit=0")
    assert resp.status_code == 422


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_pagination_limit_above_maximum_returns_422(
    client: TestClient, endpoint: str
) -> None:
    resp = client.get(f"{endpoint}?limit=201")
    assert resp.status_code == 422


@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_pagination_negative_offset_returns_422(
    client: TestClient, endpoint: str
) -> None:
    resp = client.get(f"{endpoint}?offset=-1")
    assert resp.status_code == 422

