"""Integration tests for Phase 2 CLI extensions."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from shadowlink.cli.main import main


def test_cli_generate_and_link_and_evaluate(tmp_path: Path) -> None:
    gen_dir = tmp_path / "bundle"
    ret = main(
        ["generate", "--preset", "report_abc", "--n", "20", "--out-dir", str(gen_dir)]
    )
    assert ret == 0
    assert (gen_dir / "A.csv").exists()
    assert (gen_dir / "B.csv").exists()
    assert (gen_dir / "ground_truth.csv").exists()

    # Test link
    link_out = tmp_path / "scored_pairs.csv"
    ret_link = main(
        [
            "link",
            str(gen_dir / "A.csv"),
            str(gen_dir / "B.csv"),
            "--attributes",
            "age,city",
            "--blocking-keys",
            "city",
            "--output",
            str(link_out),
        ]
    )
    assert ret_link == 0
    assert link_out.exists()

    # Test evaluate
    ret_eval = main(
        [
            "evaluate",
            str(link_out),
            str(gen_dir / "ground_truth.csv"),
            "--left-dataset",
            "A",
            "--right-dataset",
            "B",
            "--format",
            "json",
        ]
    )
    assert ret_eval == 0


def test_cli_attack(tmp_path: Path) -> None:
    # Generate wide_release
    gen_dir = tmp_path / "wide"
    main(
        [
            "generate",
            "--preset",
            "wide_release",
            "--n",
            "20",
            "--out-dir",
            str(gen_dir),
        ]
    )
    w_df = pd.read_csv(gen_dir / "W.csv")
    first_rec = w_df.iloc[0]
    rec_id = str(first_rec["record_id"])
    aux_dict = {"age": int(first_rec["age"]), "city": str(first_rec["city"])}

    ret_atk = main(
        [
            "attack",
            str(gen_dir / "W.csv"),
            "--target-id",
            rec_id,
            "--aux",
            json.dumps(aux_dict),
            "--steps",
            "age,city",
        ]
    )
    assert ret_atk == 0


def test_cli_experiment(tmp_path: Path) -> None:
    out_table = tmp_path / "table5.md"
    ret_exp = main(
        [
            "experiment",
            "table5",
            "--n",
            "20",
            "--format",
            "markdown",
            "--output",
            str(out_table),
        ]
    )
    assert ret_exp == 0
    assert out_table.exists()
    assert "Table 5" in out_table.read_text(encoding="utf-8")
