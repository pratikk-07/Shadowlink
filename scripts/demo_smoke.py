"""Automated smoke test for the SHADOWLINK Demo Dashboard API.

Exercises all endpoints sequentially, validates schemas, verifies that no
ground-truth identifiers ('entity_id') leak, and asserts system health.
"""

from __future__ import annotations

import sys
import traceback

from fastapi.testclient import TestClient

from shadowlink.api.app import app


def run_smoke_test() -> None:
    client = TestClient(app)
    print("==========================================================")
    print("  SHADOWLINK Demo Dashboard API Automated Smoke Test")
    print("==========================================================")

    # 1. GET /demo
    print("[1/9] GET /demo (Dashboard HTML) ...", end=" ")
    res = client.get("/demo")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "SHADOWLINK" in res.text
    assert "entity_id" not in res.text
    print("OK (HTML returned, 0 ground truth leaks)")

    # 2. POST /demo/api/runs
    print("[2/9] POST /demo/api/runs (Create Benchmark Run) ...", end=" ")
    res = client.post(
        "/demo/api/runs",
        json={
            "preset": "report_abc",
            "population_size": 100,
            "shared_fraction": 0.5,
            "typo_rate": 0.05,
            "missing_rate": 0.02,
            "seed": 42,
        },
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    run_id = data["run_id"]
    assert "entity_id" not in res.text
    print(f"OK (run_id={run_id})")

    # 3. GET /demo/api/runs/{run_id}/profile
    print("[3/9] GET /demo/api/runs/{id}/profile ...", end=" ")
    res = client.get(f"/demo/api/runs/{run_id}/profile")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "entity_id" not in res.text
    print("OK (profiles fetched)")

    # 4. POST /demo/api/runs/{run_id}/qi
    print("[4/9] POST /demo/api/runs/{id}/qi (Analyze Quasi-Identifiers) ...", end=" ")
    res = client.post(
        f"/demo/api/runs/{run_id}/qi",
        json={"dataset_name": "A", "qi_columns": ["age", "city"]},
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    qi_data = res.json()
    assert "k_anonymity" in qi_data
    assert "entity_id" not in res.text
    print(f"OK (k={qi_data['k_anonymity']})")

    # 5. POST /demo/api/runs/{run_id}/attack
    print("[5/9] POST /demo/api/runs/{id}/attack (Progressive Attacker) ...", end=" ")
    res = client.post(
        f"/demo/api/runs/{run_id}/attack",
        json={
            "dataset_name": "A",
            "steps": [["age", "city"], ["course"]],
            "n_targets": 20,
            "seed": 42,
        },
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    att_data = res.json()
    assert len(att_data["narrowing_curve"]) == 2
    assert "entity_id" not in res.text
    print("OK (narrowing curve evaluated)")

    # 6. POST /demo/api/runs/{run_id}/linkage
    print("[6/9] POST /demo/api/runs/{id}/linkage (Linkage Engine) ...", end=" ")
    res = client.post(
        f"/demo/api/runs/{run_id}/linkage",
        json={
            "left_dataset": "A",
            "right_dataset": "B",
            "method": "compare_all",
            "threshold": 0.85,
        },
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    lnk_data = res.json()
    assert "comparison" in lnk_data
    assert "entity_id" not in res.text
    print("OK (multi-method benchmark evaluated)")

    # 7. POST /demo/api/runs/{run_id}/mitigate
    print("[7/9] POST /demo/api/runs/{id}/mitigate (Mitigation Tradeoff) ...", end=" ")
    res = client.post(
        f"/demo/api/runs/{run_id}/mitigate",
        json={
            "dataset_name": "A",
            "qi_columns": ["age", "city"],
            "transformations": [
                {"type": "generalize_age", "kwargs": {"bin_width": 5}},
                {"type": "suppress_rare_values", "kwargs": {"min_count": 2}},
            ],
        },
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    mit_data = res.json()
    assert "before" in mit_data and "after" in mit_data
    assert "entity_id" not in res.text
    print("OK (tradeoff computed)")

    # 8. POST /demo/api/runs/{run_id}/pipeline
    print("[8/9] POST /demo/api/runs/{id}/pipeline (Full Pipeline) ...", end=" ")
    res = client.post(f"/demo/api/runs/{run_id}/pipeline")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    pipe_data = res.json()
    assert "stage8_evaluation" in pipe_data
    assert "entity_id" not in res.text
    print("OK (all 9 stages orchestrated)")

    # 9. GET /demo/api/runs/{run_id}/tables
    print("[9/9] GET /demo/api/runs/{id}/tables (Tables 5, 6, 7) ...", end=" ")
    res = client.get(f"/demo/api/runs/{run_id}/tables")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    tables_data = res.json()
    assert (
        "table5" in tables_data
        and "table6" in tables_data
        and "table7" in tables_data
    )
    assert "entity_id" not in res.text
    print("OK (tables generated)")

    print("==========================================================")
    print("  ALL DEMO ENDPOINTS PASSED SMOKE TEST SUCCESSFULLY!       ")
    print("  Ground-Truth Boundary (R3) verified: 0 leaks detected.   ")
    print("==========================================================")


if __name__ == "__main__":
    try:
        run_smoke_test()
    except Exception:
        traceback.print_exc()
        sys.exit(1)

