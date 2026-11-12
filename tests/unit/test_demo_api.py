"""Unit and integration tests for the SHADOWLINK Demo Dashboard API."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from shadowlink.api.app import app
from shadowlink.api.demo.html import DEMO_HTML


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a test client for the FastAPI application."""
    return TestClient(app)


def test_demo_html_serves_offline_and_clean(client: TestClient) -> None:
    """Verify that GET /demo serves self-contained HTML with no external resources."""
    res = client.get("/demo")
    assert res.status_code == 200
    html = res.text
    assert "<!DOCTYPE html>" in html
    assert "SHADOWLINK" in html

    # Rule R2: Must work offline. No external scripts or styles.
    # Disallow http:// and https:// external CDNs/fonts/scripts
    external_links = re.findall(
        r'(?:href|src)=["\'](https?://[^"\']+)["\']', html
    )
    for link in external_links:
        assert (
            "127.0.0.1" in link or "localhost" in link
        ), f"External network URL found in offline HTML: {link}"

    # Rule R3: Ground-truth boundary. No entity_id in the HTML.
    assert "entity_id" not in html


def test_demo_create_run_and_validation(client: TestClient) -> None:
    """Test POST /demo/api/runs with valid and invalid parameters."""
    # 1. Valid creation
    res = client.post(
        "/demo/api/runs",
        json={
            "preset": "report_abc",
            "population_size": 100,
            "shared_fraction": 0.5,
            "typo_rate": 0.05,
            "missing_rate": 0.02,
            "seed": 100,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "run_id" in data
    assert data["population_size"] == 100
    assert "A" in data["dataset_counts"]
    assert "entity_id" not in res.text

    # 2. Validation bounds: population_size too low (<50)
    res_low = client.post(
        "/demo/api/runs",
        json={"population_size": 10},
    )
    assert res_low.status_code == 422

    # 3. Validation bounds: population_size too high (>5000)
    res_high = client.post(
        "/demo/api/runs",
        json={"population_size": 6000},
    )
    assert res_high.status_code == 422

    # 4. Validation bounds: shared_fraction out of range
    res_frac = client.post(
        "/demo/api/runs",
        json={"shared_fraction": 1.5},
    )
    assert res_frac.status_code == 422


def test_demo_endpoints_full_lifecycle(client: TestClient) -> None:
    """Test full sequential lifecycle matching exact browser page requests."""
    # 1. Create Run
    res_create = client.post(
        "/demo/api/runs",
        json={
            "preset": "report_abc",
            "population_size": 80,
            "shared_fraction": 0.5,
            "seed": 42,
        },
    )
    assert res_create.status_code == 200
    run_data = res_create.json()
    run_id = run_data["run_id"]
    assert "entity_id" not in res_create.text

    # Verify run fields read by JavaScript
    for f in [
        "run_id",
        "preset",
        "population_size",
        "seed",
        "dataset_counts",
        "dataset_previews",
        "dataset_profiles",
        "stage_status",
    ]:
        assert f in run_data, f"Missing run field: {f}"

    # Extract real column names from preview
    preview_rows = run_data["dataset_previews"]["A"]
    assert len(preview_rows) > 0
    available_cols = list(preview_rows[0].keys())
    assert "entity_id" not in available_cols

    # 2. Get Profile
    res_prof = client.get(f"/demo/api/runs/{run_id}/profile")
    assert res_prof.status_code == 200
    assert "A" in res_prof.json()["profiles"]
    assert "entity_id" not in res_prof.text

    # 3. QI Analysis using real column names
    qi_cols = [c for c in ["age", "city"] if c in available_cols]
    if not qi_cols:
        qi_cols = available_cols[:2]

    res_qi = client.post(
        f"/demo/api/runs/{run_id}/qi",
        json={"dataset_name": "A", "qi_columns": qi_cols},
    )
    assert res_qi.status_code == 200
    qi_body = res_qi.json()
    assert "entity_id" not in res_qi.text

    # Verify every field read by the QI JavaScript
    for field_name in [
        "k_anonymity",
        "singleton_proportion",
        "max_risk",
        "average_risk",
        "candidate_qis",
        "shared_attributes",
        "risk_metrics",
        "equivalence_classes",
        "stage_status",
    ]:
        assert field_name in qi_body, f"QI missing field: {field_name}"

    for cand in qi_body["candidate_qis"]:
        assert "column_name" in cand
        assert "dataset_name" in cand
        assert "reasons" in cand

    for rm in qi_body["risk_metrics"]:
        assert "name" in rm
        assert "value" in rm
        assert "formula" in rm
        assert "assumption" in rm

    assert "class_sizes" in qi_body["equivalence_classes"]

    # 4. Attacker Simulation with multi-step knowledge profile
    step1_cols = [c for c in ["age", "city"] if c in available_cols] or [
        available_cols[0]
    ]
    rem_cols = [c for c in available_cols if c not in step1_cols]
    step2_cols = [rem_cols[0]] if rem_cols else step1_cols
    attack_steps = [step1_cols, step2_cols]

    res_atk = client.post(
        f"/demo/api/runs/{run_id}/attack",
        json={
            "dataset_name": "A",
            "steps": attack_steps,
            "n_targets": 15,
            "seed": 42,
        },
    )
    assert res_atk.status_code == 200
    atk_body = res_atk.json()
    assert "entity_id" not in res_atk.text

    # Verify every field read by Attacker JavaScript
    curve = atk_body.get("narrowing_curve") or atk_body.get("steps")
    assert curve is not None
    assert len(curve) == len(attack_steps)
    for step_item in curve:
        for f in [
            "step",
            "attributes",
            "mean_candidates",
            "median_candidates",
            "mean_risk",
            "unique_fraction",
            "mean_reduction",
        ]:
            assert f in step_item, f"Attacker step missing field: {f}"

    # 5. Linkage Execution across all methods
    for method in [
        "similarity",
        "deterministic",
        "fellegi_sunter",
        "compare_all",
    ]:
        res_lnk = client.post(
            f"/demo/api/runs/{run_id}/linkage",
            json={
                "left_dataset": "A",
                "right_dataset": "B",
                "method": method,
                "threshold": 0.85,
            },
        )
        assert res_lnk.status_code == 200
        lnk_body = res_lnk.json()
        assert "entity_id" not in res_lnk.text

        # Verify summary fields read by JavaScript
        for f in [
            "precision",
            "recall",
            "f1",
            "reidentification_success",
            "deterministic_reid_success",
            "tie_adjusted_reid_success",
            "runtime_seconds",
        ]:
            assert f in lnk_body, f"Linkage top-level missing field: {f}"
            assert lnk_body[f] is not None, f"Linkage top-level field {f} is null"

        assert lnk_body["f1"] is not None
        assert lnk_body["reidentification_success"] is not None

        if method == "compare_all":
            assert "comparison" in lnk_body
            for m_key, m_item in lnk_body["comparison"].items():
                for f in [
                    "threshold",
                    "precision",
                    "recall",
                    "f1",
                    "f1_score",
                    "deterministic_reid_success",
                    "tie_adjusted_reid_success",
                    "reidentification_success",
                    "runtime_seconds",
                ]:
                    assert f in m_item, f"Comparison {m_key} missing field: {f}"
                    assert (
                        m_item[f] is not None
                    ), f"Comparison {m_key} field {f} is null"

    # 6. Mitigation
    res_mit = client.post(
        f"/demo/api/runs/{run_id}/mitigate",
        json={
            "dataset_name": "A",
            "qi_columns": qi_cols,
            "transformations": [
                {"type": "generalize_age", "kwargs": {"bin_width": 5}},
            ],
        },
    )
    assert res_mit.status_code == 200
    mit_body = res_mit.json()
    assert "entity_id" not in res_mit.text
    for f in [
        "before",
        "after",
        "utility",
        "notes",
        "stage_status",
    ]:
        assert f in mit_body, f"Mitigation missing field: {f}"

    for f in [
        "k_anonymity",
        "singleton_proportion",
        "max_risk",
        "average_risk",
    ]:
        assert f in mit_body["before"]
        assert f in mit_body["after"]

    for f in [
        "discernibility_metric",
        "records_suppressed",
        "suppression_rate",
    ]:
        assert f in mit_body["utility"]

    # 7. Tables 5, 6, 7
    res_tbl = client.get(f"/demo/api/runs/{run_id}/tables")
    assert res_tbl.status_code == 200
    tbl_body = res_tbl.json()
    assert "entity_id" not in res_tbl.text
    for tk in ["table5", "table6", "table7"]:
        assert tk in tbl_body
        assert "title" in tbl_body[tk]
        assert "rows" in tbl_body[tk]
        assert "csv" in tbl_body[tk]


def test_demo_attack_unknown_column_returns_4xx(client: TestClient) -> None:
    """Verify that unknown/disallowed column in attack steps returns 4xx error."""
    res_create = client.post(
        "/demo/api/runs",
        json={"population_size": 60, "seed": 77},
    )
    run_id = res_create.json()["run_id"]

    # 1. Non-existent column name
    res_unknown = client.post(
        f"/demo/api/runs/{run_id}/attack",
        json={
            "dataset_name": "A",
            "steps": [["age", "non_existent_column_xyz"]],
            "n_targets": 10,
        },
    )
    assert res_unknown.status_code == 400
    assert "unknown column" in res_unknown.json()["detail"].lower()

    # 2. Disallowed ground-truth column
    res_forbidden = client.post(
        f"/demo/api/runs/{run_id}/attack",
        json={
            "dataset_name": "A",
            "steps": [["age", "entity_id"]],
            "n_targets": 10,
        },
    )
    assert res_forbidden.status_code == 400
    assert "forbidden" in res_forbidden.json()["detail"].lower()


def test_demo_frontend_js_contract_syntax() -> None:
    """Contract test: extract JS from DEMO_HTML and verify using node --check."""
    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("Node.js is not installed; skipping JS contract syntax check.")

    script_matches = re.findall(r"<script>(.*?)</script>", DEMO_HTML, re.DOTALL)
    assert len(script_matches) > 0, "No <script> tag found in DEMO_HTML"
    js_content = script_matches[0]

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as f:
        f.write(js_content)
        tmp_path = Path(f.name)

    try:
        proc = subprocess.run(
            [node_bin, "--check", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert (
            proc.returncode == 0
        ), f"JavaScript syntax error in DEMO_HTML:\n{proc.stderr}"
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def test_demo_unknown_run_returns_404(client: TestClient) -> None:
    """Verify that accessing non-existent or evicted runs returns 404."""
    unknown_id = "run_non_existent_9999"
    res = client.get(f"/demo/api/runs/{unknown_id}/profile")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    res_qi = client.post(
        f"/demo/api/runs/{unknown_id}/qi",
        json={"dataset_name": "A", "qi_columns": ["age"]},
    )
    assert res_qi.status_code == 404


def test_demo_determinism(client: TestClient) -> None:
    """Verify that same seed and configuration produce identical metrics (Rule R6)."""
    payload: dict[str, Any] = {
        "preset": "report_abc",
        "population_size": 60,
        "shared_fraction": 0.5,
        "seed": 999,
    }
    res1 = client.post("/demo/api/runs", json=payload)
    res2 = client.post("/demo/api/runs", json=payload)
    assert res1.status_code == 200
    assert res2.status_code == 200

    d1 = res1.json()
    d2 = res2.json()
    assert d1["dataset_counts"] == d2["dataset_counts"]
    assert d1["dataset_previews"] == d2["dataset_previews"]


def test_demo_lru_eviction(client: TestClient) -> None:
    """Verify that in-memory cache holds at most 5 runs and evicts oldest (R6)."""
    created_ids: list[str] = []
    # Create 6 runs
    for i in range(6):
        res = client.post(
            "/demo/api/runs",
            json={
                "preset": "report_abc",
                "population_size": 50,
                "seed": 100 + i,
            },
        )
        assert res.status_code == 200
        created_ids.append(res.json()["run_id"])

    # First created run should now be evicted (404)
    first_id = created_ids[0]
    res_evicted = client.get(f"/demo/api/runs/{first_id}/profile")
    assert res_evicted.status_code == 404

    # Latest run should be available (200)
    latest_id = created_ids[-1]
    res_latest = client.get(f"/demo/api/runs/{latest_id}/profile")
    assert res_latest.status_code == 200
