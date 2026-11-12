"""Configuration models and structured report types for the end-to-end pipeline."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from shadowlink.common.exceptions import ValidationError
from shadowlink.mitigation.models import TransformationSpec


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for end-to-end execution of all SHADOWLINK modules."""

    seed: int = 42
    generator_preset: str = "report_abc"
    population_size: int = 100
    shared_fraction: float = 0.5
    typo_rate: float = 0.05
    missing_rate: float = 0.02
    target_dataset: str = "A"
    qi_columns: list[str] = field(default_factory=lambda: ["age", "city"])
    attacker_steps: list[tuple[str, ...]] = field(
        default_factory=lambda: [("age", "city"), ("course",)]
    )
    attacker_targets: int = 50
    linkage_left: str = "A"
    linkage_right: str = "B"
    linkage_blocking_keys: list[str] = field(default_factory=lambda: ["city"])
    linkage_attributes: list[str] = field(
        default_factory=lambda: ["age", "city"]
    )
    linkage_threshold: float = 0.85
    mitigation_transformations: list[TransformationSpec] = field(
        default_factory=list
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineConfig:
        seed = int(data.get("seed", 42))

        gen_data = data.get("generator", {})
        gen_preset = str(gen_data.get("preset", "report_abc"))
        pop_size = int(gen_data.get("population_size", 100))
        shared_frac = float(gen_data.get("shared_fraction", 0.5))
        typo_r = float(gen_data.get("typo_rate", 0.05))
        missing_r = float(gen_data.get("missing_rate", 0.02))

        qi_data = data.get("qi_analyser", {})
        target_ds = str(qi_data.get("target_dataset", "A"))
        qi_cols = list(qi_data.get("qi_columns", ["age", "city"]))

        atk_data = data.get("attacker", {})
        raw_steps = atk_data.get("steps", [["age", "city"], ["course"]])
        steps = [tuple(step) for step in raw_steps]
        atk_targets = int(atk_data.get("n_targets", 50))

        link_data = data.get("linkage", {})
        left_ds = str(link_data.get("left_dataset", "A"))
        right_ds = str(link_data.get("right_dataset", "B"))
        b_keys = list(link_data.get("blocking_keys", ["city"]))
        l_attrs = list(link_data.get("attributes", ["age", "city"]))
        thresh = float(link_data.get("threshold", 0.85))

        mit_data = data.get("mitigation", {})
        raw_txs = mit_data.get("transformations", [])
        tx_specs = [
            TransformationSpec(
                kind=t["kind"], parameters=t.get("parameters", {})
            )
            for t in raw_txs
        ]

        return cls(
            seed=seed,
            generator_preset=gen_preset,
            population_size=pop_size,
            shared_fraction=shared_frac,
            typo_rate=typo_r,
            missing_rate=missing_r,
            target_dataset=target_ds,
            qi_columns=qi_cols,
            attacker_steps=steps,
            attacker_targets=atk_targets,
            linkage_left=left_ds,
            linkage_right=right_ds,
            linkage_blocking_keys=b_keys,
            linkage_attributes=l_attrs,
            linkage_threshold=thresh,
            mitigation_transformations=tx_specs,
        )

    @classmethod
    def from_json(cls, path_or_str: str | Path) -> PipelineConfig:
        p = Path(path_or_str)
        if p.exists() and p.is_file():
            raw_text = p.read_text(encoding="utf-8")
        else:
            raw_text = str(path_or_str)
        try:
            parsed = json.loads(raw_text)
        except Exception as exc:
            raise ValidationError(
                f"Failed to parse pipeline JSON configuration: {exc}."
            ) from exc
        return cls.from_dict(parsed)

    def to_dict(self) -> dict[str, Any]:
        tx_list = [asdict(tx) for tx in self.mitigation_transformations]
        return {
            "seed": self.seed,
            "generator": {
                "preset": self.generator_preset,
                "population_size": self.population_size,
                "shared_fraction": self.shared_fraction,
                "typo_rate": self.typo_rate,
                "missing_rate": self.missing_rate,
            },
            "qi_analyser": {
                "target_dataset": self.target_dataset,
                "qi_columns": self.qi_columns,
            },
            "attacker": {
                "steps": [list(step) for step in self.attacker_steps],
                "n_targets": self.attacker_targets,
            },
            "linkage": {
                "left_dataset": self.linkage_left,
                "right_dataset": self.linkage_right,
                "blocking_keys": self.linkage_blocking_keys,
                "attributes": self.linkage_attributes,
                "threshold": self.linkage_threshold,
            },
            "mitigation": {"transformations": tx_list},
        }


@dataclass
class PipelineReport:
    """Comprehensive artifact capturing metrics from all 9 stages."""

    metadata: dict[str, Any]
    stage1_generation: dict[str, Any]
    stage2_profiles: dict[str, Any]
    stage3_shared_and_qis: dict[str, Any]
    stage4_risk: dict[str, Any]
    stage5_attacker: dict[str, Any]
    stage6_linkage: dict[str, Any]
    stage7_mitigation: dict[str, Any]
    stage8_evaluation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata,
            "stage1_generation": self.stage1_generation,
            "stage2_profiles": self.stage2_profiles,
            "stage3_shared_and_qis": self.stage3_shared_and_qis,
            "stage4_risk": self.stage4_risk,
            "stage5_attacker": self.stage5_attacker,
            "stage6_linkage": self.stage6_linkage,
            "stage7_mitigation": self.stage7_mitigation,
            "stage8_evaluation": self.stage8_evaluation,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        """Render a GitHub-flavored Markdown document with every metric."""
        lines: list[str] = []
        lines.append("# SHADOWLINK End-to-End Pipeline Audit Report\n")

        # Metadata
        lines.append("## 1. Execution Metadata & Provenance\n")
        lines.append(f"- **Seed**: `{self.metadata.get('seed')}`")
        lines.append(
            f"- **Population Size**: `{self.metadata.get('population_size')}`"
        )
        lines.append(
            f"- **Python Version**: `{self.metadata.get('python_version')}`"
        )
        lines.append(
            f"- **Pandas Version**: `{self.metadata.get('pandas_version')}`"
        )
        lines.append(
            f"- **Numpy Version**: `{self.metadata.get('numpy_version')}`\n"
        )

        # Stage 1
        lines.append("## 2. Stage 1 — Synthetic Data Generation\n")
        lines.append(f"- **Preset**: `{self.stage1_generation.get('preset')}`")
        sh_frac = self.stage1_generation.get("shared_fraction")
        lines.append(f"- **Shared Fraction**: `{sh_frac}`")
        tot_typos = self.stage1_generation.get("total_typos")
        lines.append(f"- **Injected Typos**: `{tot_typos}`")
        tot_missing = self.stage1_generation.get("total_missing")
        lines.append(f"- **Injected Missing Values**: `{tot_missing}`")
        counts = self.stage1_generation.get("record_counts", {})
        lines.append("- **Record Counts per Dataset**:")
        for ds, c in counts.items():
            lines.append(f"  - Dataset `{ds}`: {c} records")
        lines.append("")

        # Stage 2
        lines.append("## 3. Stage 2 — Dataset Profiling\n")
        for ds, prof in self.stage2_profiles.items():
            rw = prof.get("rows")
            cl = prof.get("columns")
            lines.append(f"### Dataset `{ds}`: {rw} rows, {cl} columns")
            cols = prof.get("column_details", [])
            lines.append("| Column | Type | Distinct | Missing Rate | Uniqueness |")
            lines.append("|---|---|---|---|---|")
            for c in cols:
                u_str = (
                    f"{c['uniqueness_ratio']:.4f}"
                    if c.get("uniqueness_ratio") is not None
                    else "N/A"
                )
                m_str = (
                    f"{c['missing_rate']:.4f}"
                    if c.get("missing_rate") is not None
                    else "0.0000"
                )
                c_name = c["name"]
                c_kind = c["kind"]
                c_dist = c["distinct_count"]
                lines.append(
                    f"| {c_name} | {c_kind} | {c_dist} | {m_str} | {u_str} |"
                )
            lines.append("")

        # Stage 3
        lines.append("## 4. Stage 3 — Shared Attributes & Quasi-Identifiers\n")
        sh_attrs = self.stage3_shared_and_qis.get("shared_attributes")
        lines.append(f"- **Shared Attributes**: `{sh_attrs}`")
        cand_qis = self.stage3_shared_and_qis.get("candidate_qis")
        lines.append(f"- **Detected Candidate QIs**: `{cand_qis}`\n")

        # Stage 4
        lines.append("## 5. Stage 4 — Equivalence Classes & Baseline Risk\n")
        tgt_ds = self.stage4_risk.get("target_dataset")
        lines.append(f"- **Target Dataset**: `{tgt_ds}`")
        q_cols = self.stage4_risk.get("qi_columns")
        lines.append(f"- **Analyzed QIs**: `{q_cols}`")
        n_cls = self.stage4_risk.get("num_classes")
        lines.append(f"- **Equivalence Classes ($|EC|$)**: {n_cls}")
        k_val = self.stage4_risk.get("k")
        lines.append(f"- **Minimal Class Size ($k$)**: {k_val}")
        u_val = self.stage4_risk.get("uniqueness", 0.0)
        lines.append(f"- **Uniqueness Proportion ($k=1$)**: {u_val:.4f}")
        mx_risk = self.stage4_risk.get("max_class_risk", 0.0)
        lines.append(f"- **Max Class Risk**: {mx_risk:.4f}")
        av_risk = self.stage4_risk.get("average_class_risk", 0.0)
        lines.append(f"- **Average Class Risk**: {av_risk:.4f}")
        dm_val = self.stage4_risk.get("discernibility_metric")
        lines.append(f"- **Discernibility Metric (DM)**: {dm_val}\n")

        # Stage 5
        lines.append("## 6. Stage 5 — Attacker Narrowing Curve\n")
        lines.append(
            "| Step | Attributes | Mean Candidates | Mean Risk "
            "| Unique Fraction | Expected Success |"
        )
        lines.append("|---|---|---|---|---|---|")
        for s in self.stage5_attacker.get("steps", []):
            st = s["step"]
            at = s["attributes"]
            mc = s["mean_candidates"]
            mr = s["mean_risk"]
            uf = s["unique_fraction"]
            es = s["expected_success"]
            lines.append(
                f"| {st} | {at} | {mc:.4f} | {mr:.4f} | {uf:.4f} | {es:.4f} |"
            )
        lines.append("")

        # Stage 6
        lines.append("## 7. Stage 6 — Record Linkage Execution\n")
        l_ds = self.stage6_linkage.get("left_dataset")
        r_ds = self.stage6_linkage.get("right_dataset")
        lines.append(f"- **Pair Comparison**: `{l_ds}` vs `{r_ds}`")
        b_k = self.stage6_linkage.get("blocking_keys")
        lines.append(f"- **Blocking Keys**: `{b_k}`")
        cp_cnt = self.stage6_linkage.get("candidate_pairs_count")
        lines.append(f"- **Candidate Pairs**: {cp_cnt}")
        rr_val = self.stage6_linkage.get("reduction_ratio", 0.0)
        lines.append(f"- **Reduction Ratio (RR)**: {rr_val:.4f}\n")

        # Stage 7
        lines.append("## 8. Stage 7 — Privacy Mitigation Impact\n")
        tx_app = self.stage7_mitigation.get("applied_transformations")
        lines.append(f"- **Applied Transformations**: {tx_app}")
        u_loss = self.stage7_mitigation.get("utility_loss", 0.0)
        lines.append(f"- **Cell Utility Loss**: {u_loss:.4f}")
        b_r = self.stage7_mitigation.get("baseline_average_risk", 0.0)
        m_r = self.stage7_mitigation.get("mitigated_average_risk", 0.0)
        lines.append(
            f"- **Risk Reduction**: Average class risk changed from "
            f"{b_r:.4f} to {m_r:.4f}"
        )
        b_k = self.stage7_mitigation.get("baseline_k")
        m_k = self.stage7_mitigation.get("mitigated_k")
        lines.append(f"- **Minimal Class Size ($k$)**: From {b_k} to {m_k}\n")

        # Stage 8
        lines.append("## 9. Stage 8 — Ground Truth Evaluation\n")
        lines.append(
            "> *Evaluator is the ONLY module permitted to access ground truth.*\n"
        )
        lines.append(
            "| Method | Baseline Precision | Baseline Recall "
            "| Baseline F1 | Mitigated F1 |"
        )
        lines.append("|---|---|---|---|---|")
        for m, vals in self.stage8_evaluation.get("methods", {}).items():
            p = vals["orig_precision"]
            r = vals["orig_recall"]
            f1 = vals["orig_f1"]
            mf1 = vals["mit_f1"]
            lines.append(f"| {m} | {p:.4f} | {r:.4f} | {f1:.4f} | {mf1:.4f} |")
        lines.append("")
        t_reid = self.stage8_evaluation.get("tie_adjusted_reid_success", 0.0)
        lines.append(
            f"- **Tie-Adjusted Re-Identification Success**: {t_reid:.4f}"
        )
        d_reid = self.stage8_evaluation.get("deterministic_reid_success", 0.0)
        lines.append(
            f"- **Deterministic Re-Identification Success**: {d_reid:.4f}"
        )
        pc_val = self.stage8_evaluation.get("pairs_completeness", 0.0)
        lines.append(f"- **Blocking Pairs Completeness**: {pc_val:.4f}\n")

        return "\n".join(lines)
