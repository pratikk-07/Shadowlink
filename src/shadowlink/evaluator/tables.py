"""Table formatting utilities for benchmark and experiment reports."""

from __future__ import annotations

import datetime
from typing import Any

import numpy as np
import pandas as pd


def generate_experiment_metadata(
    experiment_name: str,
    n: int,
    seed: int,
    shared_fraction: float | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> str:
    """Generate standardized reproducibility comment header."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    lines = [
        f"# Experiment: {experiment_name}",
        f"# Generated: {now_iso}",
        f"# Population N: {n}",
        f"# Seed: {seed}",
    ]
    if shared_fraction is not None:
        lines.append(f"# Shared Fraction: {shared_fraction}")
    lines.append(f"# Pandas: {pd.__version__}, Numpy: {np.__version__}")
    if extra_metadata:
        for k, v in extra_metadata.items():
            lines.append(f"# {k}: {v}")
    lines.append("")
    return "\n".join(lines)


def format_markdown_table(df: pd.DataFrame, title: str = "") -> str:
    """Format DataFrame as GitHub-flavored Markdown table with optional title."""
    headers = list(df.columns)
    col_widths = [len(str(h)) for h in headers]

    rows_str: list[list[str]] = []
    for _, row in df.iterrows():
        r_strs = []
        for i, h in enumerate(headers):
            val = row[h]
            if isinstance(val, (float, np.floating)):
                formatted = f"{val:.4f}"
            else:
                formatted = str(val)
            r_strs.append(formatted)
            col_widths[i] = max(col_widths[i], len(formatted))
        rows_str.append(r_strs)

    # Build markdown
    out: list[str] = []
    if title:
        out.append(f"### {title}\n")

    cols_hdr = [h.ljust(col_widths[i]) for i, h in enumerate(headers)]
    header_line = "| " + " | ".join(cols_hdr) + " |"
    seps = ["-" * col_widths[i] for i in range(len(headers))]
    sep_line = "|-" + "-|-".join(seps) + "-|"
    out.append(header_line)
    out.append(sep_line)

    for r in rows_str:
        cols_row = [r[i].ljust(col_widths[i]) for i in range(len(headers))]
        line = "| " + " | ".join(cols_row) + " |"
        out.append(line)

    return "\n".join(out) + "\n"


def format_csv_with_header(
    df: pd.DataFrame,
    metadata_header: str,
) -> str:
    """Combine metadata comment header and CSV table."""
    csv_body = df.to_csv(index=False)
    return metadata_header + csv_body
