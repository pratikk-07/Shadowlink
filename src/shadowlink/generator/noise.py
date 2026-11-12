"""Noise injection algorithms: realistic character typos and attribute missingness."""

from __future__ import annotations

import string

import numpy as np
import pandas as pd

TYPO_CHARS = string.ascii_letters


def inject_typo(text: str, rng: np.random.Generator) -> str:
    """Inject exactly one character typo into a non-empty string.

    Possible operations:
    1. Substitution: replace one character with a random letter.
    2. Deletion: remove one character (only if len > 1).
    3. Insertion: insert one random letter.
    4. Transposition: swap two adjacent characters (only if len >= 2 and chars differ).

    Invariants:
    - Result is never empty.
    - Result is strictly different from the input string.
    """
    if not text:
        return str(rng.choice(list(TYPO_CHARS)))

    n = len(text)
    ops: list[str] = ["insert", "substitute"]
    if n > 1:
        ops.append("delete")
        if any(text[i] != text[i + 1] for i in range(n - 1)):
            ops.append("transpose")

    op = rng.choice(ops)

    if op == "delete":
        idx = int(rng.integers(0, n))
        res = text[:idx] + text[idx + 1 :]
        if res != text and res:
            return res
        # Fallback to substitution if deletion produced identical string
        op = "substitute"

    if op == "transpose":
        candidates = [i for i in range(n - 1) if text[i] != text[i + 1]]
        if candidates:
            idx = int(rng.choice(candidates))
            chars = list(text)
            chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
            return "".join(chars)
        op = "substitute"

    if op == "substitute":
        idx = int(rng.integers(0, n))
        orig_char = text[idx]
        avail = [c for c in TYPO_CHARS if c != orig_char]
        new_char = str(rng.choice(avail))
        return text[:idx] + new_char + text[idx + 1 :]

    # op == "insert"
    idx = int(rng.integers(0, n + 1))
    new_char = str(rng.choice(list(TYPO_CHARS)))
    return text[:idx] + new_char + text[idx:]


def apply_noise(
    df: pd.DataFrame,
    typo_rate: float,
    missing_rate: float,
    rng: np.random.Generator,
    id_column: str = "record_id",
) -> tuple[pd.DataFrame, int, int]:
    """Apply typos and missingness to non-identifier columns of a DataFrame.

    Returns:
        tuple of (noisy_df, typos_injected, missing_injected)
    """
    noisy_df = df.copy(deep=True)
    target_cols = [c for c in noisy_df.columns if c != id_column]
    typos_injected = 0
    missing_injected = 0

    for col in target_cols:
        series = noisy_df[col]
        is_string = pd.api.types.is_string_dtype(series) or series.dtype == object

        new_vals: list[object] = []
        for val in series:
            if pd.isna(val) or val is None:
                new_vals.append(None)
                continue

            # Check missingness first
            if missing_rate > 0.0 and rng.random() < missing_rate:
                new_vals.append(None)
                missing_injected += 1
                continue

            # Check typo on string columns
            if is_string and typo_rate > 0.0 and rng.random() < typo_rate:
                orig_str = str(val)
                noisy_str = inject_typo(orig_str, rng)
                new_vals.append(noisy_str)
                typos_injected += 1
                continue

            new_vals.append(val)

        noisy_df[col] = new_vals

    return noisy_df, typos_injected, missing_injected
