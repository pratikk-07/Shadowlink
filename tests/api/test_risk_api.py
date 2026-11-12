"""Tests for the risk endpoints (POST /risk, GET /risk/{id}, GET /risk)."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

FIXTURE_A = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "fixtures", "tiny_people_a.csv")
)


class TestPostRisk:
    def test_create_risk_returns_201(self, client: TestClient) -> None:
        resp = client.post(
            "/risk",
            json={"csv_path": FIXTURE_A, "qi_columns": ["age", "city"]},
        )
        assert resp.status_code == 201

    def test_create_risk_has_metrics(self, client: TestClient) -> None:
        data = client.post(
            "/risk",
            json={"csv_path": FIXTURE_A, "qi_columns": ["age", "city"]},
        ).json()
        assert "metrics" in data
        assert isinstance(data["metrics"], list)
        assert len(data["metrics"]) > 0

    def test_create_risk_golden_k(self, client: TestClient) -> None:
        """QI [age, city] on fixture A: k=1 (hand-verified)."""
        data = client.post(
            "/risk",
            json={"csv_path": FIXTURE_A, "qi_columns": ["age", "city"]},
        ).json()
        metrics_map = {m["name"]: m["value"] for m in data["metrics"]}
        assert metrics_map["k_anonymity"] == 1

    def test_create_risk_golden_avg_risk(self, client: TestClient) -> None:
        """Average class risk = 5/8 = 0.625 (hand-verified)."""
        data = client.post(
            "/risk",
            json={"csv_path": FIXTURE_A, "qi_columns": ["age", "city"]},
        ).json()
        metrics_map = {m["name"]: m["value"] for m in data["metrics"]}
        assert abs(metrics_map["average_class_risk"] - 5 / 8) < 1e-9

    def test_create_risk_forbidden_field_returns_422(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/risk",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age"],
                "true_id": "forbidden",
            },
        )
        assert resp.status_code == 422

    def test_create_risk_bad_path_returns_400(self, client: TestClient) -> None:
        resp = client.post(
            "/risk",
            json={"csv_path": "/no/such/file.csv", "qi_columns": ["age"]},
        )
        assert resp.status_code == 400

    def test_create_risk_empty_qi_columns_returns_422(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/risk",
            json={"csv_path": FIXTURE_A, "qi_columns": []},
        )
        assert resp.status_code == 422

    def test_create_risk_all_three_qi_golden(self, client: TestClient) -> None:
        """QI [age, city, course]: 7 classes, k=1, avg=7/8 (hand-verified)."""
        data = client.post(
            "/risk",
            json={
                "csv_path": FIXTURE_A,
                "qi_columns": ["age", "city", "course"],
            },
        ).json()
        metrics_map = {m["name"]: m["value"] for m in data["metrics"]}
        assert metrics_map["k_anonymity"] == 1
        assert abs(metrics_map["average_class_risk"] - 7 / 8) < 1e-9


class TestGetRisk:
    def test_get_risk_returns_200(self, client: TestClient) -> None:
        created = client.post(
            "/risk",
            json={"csv_path": FIXTURE_A, "qi_columns": ["age", "city"]},
        ).json()
        resp = client.get(f"/risk/{created['id']}")
        assert resp.status_code == 200

    def test_get_risk_matches_created(self, client: TestClient) -> None:
        created = client.post(
            "/risk",
            json={"csv_path": FIXTURE_A, "qi_columns": ["age", "city"]},
        ).json()
        fetched = client.get(f"/risk/{created['id']}").json()
        assert fetched["id"] == created["id"]
        assert fetched["qi_columns"] == ["age", "city"]

    def test_get_risk_not_found_returns_404(self, client: TestClient) -> None:
        resp = client.get("/risk/99999")
        assert resp.status_code == 404

    def test_list_risks_returns_list(self, client: TestClient) -> None:
        client.post(
            "/risk", json={"csv_path": FIXTURE_A, "qi_columns": ["age", "city"]}
        )
        resp = client.get("/risk")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

