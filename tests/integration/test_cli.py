"""Integration tests for the SHADOWLINK CLI interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from shadowlink.cli.main import main

FIXTURE_A_PATH = "tests/fixtures/tiny_people_a.csv"
FIXTURE_B_PATH = "tests/fixtures/tiny_people_b.csv"


class TestCLISubcommands:
    """Verify execution of CLI subcommands."""

    def test_cli_profile_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["profile", FIXTURE_A_PATH, "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["row_count"] == 8
        assert data["column_count"] == 3
        assert data["duplicate_row_count"] == 1

    def test_cli_profile_text(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["profile", FIXTURE_A_PATH, "--format", "text"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "Profile for" in captured.out
        assert "duplicate_row_count: 1" in captured.out

    def test_cli_classes(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(
            ["classes", FIXTURE_A_PATH, "--qi", "age,city", "--format", "json"]
        )
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["num_classes"] == 5
        assert data["k"] == 1
        assert data["singleton_record_count"] == 2

    def test_cli_risk(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(
            ["risk", FIXTURE_A_PATH, "--qi", "age,city", "--format", "json"]
        )
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        metrics = {m["name"]: m["value"] for m in data["metrics"]}
        assert metrics["k_anonymity"] == 1.0
        assert metrics["max_class_risk"] == 1.0
        assert metrics["average_class_risk"] == pytest.approx(0.625)

    def test_cli_candidates(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(
            ["candidates", FIXTURE_A_PATH, FIXTURE_B_PATH, "--format", "json"]
        )
        assert exit_code == 0
        captured = capsys.readouterr()
        candidates = json.loads(captured.out)
        cand_names = [c["column_name"] for c in candidates]
        assert "age" in cand_names
        assert "city" in cand_names

    def test_cli_shared(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["shared", FIXTURE_A_PATH, FIXTURE_B_PATH, "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "age" in data
        assert "city" in data

    def test_cli_mitigate(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        config_path = tmp_path / "config.json"
        config_content = [
            {
                "kind": "generalize_age",
                "parameters": {"column": "age", "bin_width": 5, "base": 0},
            },
            {
                "kind": "suppress_small_classes",
                "parameters": {"qi_columns": ["age", "city"], "k": 2},
            },
        ]
        config_path.write_text(json.dumps(config_content), encoding="utf-8")

        output_file = tmp_path / "mitigation_report.json"
        exit_code = main(
            [
                "mitigate",
                FIXTURE_A_PATH,
                "--qi",
                "age,city",
                "--config",
                str(config_path),
                "--output",
                str(output_file),
                "--format",
                "json",
            ]
        )
        assert exit_code == 0
        assert output_file.exists()
        rep_data = json.loads(output_file.read_text(encoding="utf-8"))
        assert rep_data["after"]["k"] == 3


class TestCLIErrorHandling:
    """Verify that expected errors exit with code 2 without ugly stack traces."""

    def test_missing_file_exits_2(self, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = main(["profile", "non_existent_file.csv"])
        assert exit_code == 2
        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Traceback" not in captured.err

    def test_invalid_qi_column_exits_2(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["risk", FIXTURE_A_PATH, "--qi", "nonexistent_col"])
        assert exit_code == 2
        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Traceback" not in captured.err

    def test_forbidden_column_exits_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("age,ground_truth\n20,101\n", encoding="utf-8")
        exit_code = main(["profile", str(bad_csv)])
        assert exit_code == 2
        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "forbidden" in captured.err
        assert "Traceback" not in captured.err
