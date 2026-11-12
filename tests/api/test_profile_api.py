"""Tests for the profile endpoints (POST /profile, GET /profile/{id}, GET /profile)."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

FIXTURE_A = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "tiny_people_a.csv"
)
FIXTURE_A = os.path.abspath(FIXTURE_A)


class TestPostProfile:
    def test_create_profile_returns_201(self, client: TestClient) -> None:
        resp = client.post("/profile", json={"csv_path": FIXTURE_A})
        assert resp.status_code == 201

    def test_create_profile_body_has_id(self, client: TestClient) -> None:
        resp = client.post("/profile", json={"csv_path": FIXTURE_A})
        data = resp.json()
        assert "id" in data
        assert isinstance(data["id"], int)

    def test_create_profile_row_count(self, client: TestClient) -> None:
        """Fixture A has 8 rows."""
        data = client.post("/profile", json={"csv_path": FIXTURE_A}).json()
        assert data["row_count"] == 8

    def test_create_profile_column_count(self, client: TestClient) -> None:
        """Fixture A has 3 columns."""
        data = client.post("/profile", json={"csv_path": FIXTURE_A}).json()
        assert data["column_count"] == 3

    def test_create_profile_dataset_name_override(self, client: TestClient) -> None:
        data = client.post(
            "/profile", json={"csv_path": FIXTURE_A, "dataset_name": "my_dataset"}
        ).json()
        assert data["dataset_name"] == "my_dataset"

    def test_create_profile_bad_path_returns_400(self, client: TestClient) -> None:
        resp = client.post("/profile", json={"csv_path": "/no/such/file.csv"})
        assert resp.status_code == 400
        assert "detail" in resp.json()

    def test_create_profile_forbidden_field_returns_422(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/profile",
            json={"csv_path": FIXTURE_A, "ground_truth": "some_value"},
        )
        assert resp.status_code == 422

    def test_create_profile_has_columns_list(self, client: TestClient) -> None:
        data = client.post("/profile", json={"csv_path": FIXTURE_A}).json()
        assert isinstance(data["columns"], list)
        assert len(data["columns"]) == 3

    def test_create_profile_column_has_required_fields(
        self, client: TestClient
    ) -> None:
        data = client.post("/profile", json={"csv_path": FIXTURE_A}).json()
        col = data["columns"][0]
        for field in ("name", "dtype", "kind", "missing_count", "distinct_count"):
            assert field in col, f"Missing field: {field}"


class TestGetProfile:
    def test_get_profile_returns_200(self, client: TestClient) -> None:
        created = client.post("/profile", json={"csv_path": FIXTURE_A}).json()
        resp = client.get(f"/profile/{created['id']}")
        assert resp.status_code == 200

    def test_get_profile_matches_created(self, client: TestClient) -> None:
        created = client.post("/profile", json={"csv_path": FIXTURE_A}).json()
        fetched = client.get(f"/profile/{created['id']}").json()
        assert fetched["id"] == created["id"]
        assert fetched["row_count"] == created["row_count"]

    def test_get_profile_not_found_returns_404(self, client: TestClient) -> None:
        resp = client.get("/profile/99999")
        assert resp.status_code == 404

    def test_list_profiles_returns_list(self, client: TestClient) -> None:
        client.post("/profile", json={"csv_path": FIXTURE_A})
        client.post("/profile", json={"csv_path": FIXTURE_A})
        resp = client.get("/profile")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

