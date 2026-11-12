"""Tests for the mitigation endpoints (POST /mitigate, GET /mitigate/{id})."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

FIXTURE_A = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fixtures", "tiny_people_a.csv")
)

# Pipeline: generalize age then suppress rare values in city
_SPECS = [
    {
        "kind": "generalize_age",
        "parameters": {"column": "age", "bin_width": 5, "base": 0},
    },
    {
        "kind": "suppress_rare_values",
        "parameters": {"column": "city", "minimum_frequency": 2},
    },
]


class TestPostMitigate:
    def test_create_mitigation_returns_201(self, client: TestClient) -> None:
        resp = client.post(
            "/mitigate",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age", "city"],
                "specs": _SPECS,
            },
        )
        assert resp.status_code == 201

    def test_create_mitigation_has_id(self, client: TestClient) -> None:
        data = client.post(
            "/mitigate",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age", "city"],
                "specs": _SPECS,
            },
        ).json()
        assert "id" in data
        assert isinstance(data["id"], int)

    def test_create_mitigation_before_k_is_one(self, client: TestClient) -> None:
        """Before mitigation: QI [age, city] on fixture A → k=1 (hand-verified)."""
        data = client.post(
            "/mitigate",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age", "city"],
                "specs": _SPECS,
            },
        ).json()
        assert data["before_k"] == 1

    def test_create_mitigation_steps_applied(self, client: TestClient) -> None:
        data = client.post(
            "/mitigate",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age", "city"],
                "specs": _SPECS,
            },
        ).json()
        assert data["steps_applied"] == len(_SPECS)

    def test_create_mitigation_forbidden_field_returns_422(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/mitigate",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age"],
                "specs": _SPECS,
                "identity_key": "forbidden",
            },
        )
        assert resp.status_code == 422

    def test_create_mitigation_bad_path_returns_400(self, client: TestClient) -> None:
        resp = client.post(
            "/mitigate",
            json={
                "csv_path": "/no/such/file.csv",
                "qi_columns": ["age"],
                "specs": _SPECS,
            },
        )
        assert resp.status_code == 400

    def test_create_mitigation_empty_specs_returns_422(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/mitigate",
            json={"csv_path": FIXTURE_A, "qi_columns": ["age"], "specs": []},
        )
        assert resp.status_code == 422

    def test_create_mitigation_unknown_kind_returns_400(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/mitigate",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age"],
                "specs": [{"kind": "nonexistent_transform", "parameters": {}}],
            },
        )
        assert resp.status_code == 400

    def test_create_mitigation_payload_has_before_after(
        self, client: TestClient
    ) -> None:
        data = client.post(
            "/mitigate",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age", "city"],
                "specs": _SPECS,
            },
        ).json()
        payload = data["payload"]
        assert "before" in payload
        assert "after" in payload


class TestGetMitigate:
    def test_get_mitigation_returns_200(self, client: TestClient) -> None:
        created = client.post(
            "/mitigate",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age", "city"],
                "specs": _SPECS,
            },
        ).json()
        resp = client.get(f"/mitigate/{created['id']}")
        assert resp.status_code == 200

    def test_get_mitigation_matches_created(self, client: TestClient) -> None:
        created = client.post(
            "/mitigate",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age", "city"],
                "specs": _SPECS,
            },
        ).json()
        fetched = client.get(f"/mitigate/{created['id']}").json()
        assert fetched["id"] == created["id"]
        assert fetched["qi_columns"] == ["age", "city"]

    def test_get_mitigation_not_found_returns_404(self, client: TestClient) -> None:
        resp = client.get("/mitigate/99999")
        assert resp.status_code == 404

    def test_list_mitigations_returns_list(self, client: TestClient) -> None:
        client.post(
            "/mitigate",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age", "city"],
                "specs": _SPECS,
            },
        )
        resp = client.get("/mitigate")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

