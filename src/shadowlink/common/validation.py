"""Input validation helpers for SHADOWLINK.

Safety boundary
---------------
SHADOWLINK is a **defensive** privacy-engineering tool.  It must never
receive, process, or store ground-truth identity information.  Every public
function that accepts a ``pd.DataFrame`` must call
``validate_no_forbidden_columns`` before accessing any column values.

Forbidden column names (checked case-insensitively after stripping whitespace):

    ground_truth, true_id, true_identity, identity_key

If any of these appear in the input DataFrame, a ``ValidationError`` is raised
immediately with an actionable message telling the caller to remove the column.

A companion test (``tests/unit/test_validation.py::TestPublicFunctionSignatures``)
walks the entire ``shadowlink`` package tree and asserts that **no public
function parameter** carries a forbidden name either.
"""

from __future__ import annotations

import pandas as pd

from shadowlink.common.exceptions import ValidationError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FORBIDDEN_COLUMN_NAMES: frozenset[str] = frozenset(
    {
        "ground_truth",
        "true_id",
        "true_identity",
        "identity_key",
    }
)
"""Column names that SHADOWLINK refuses to accept in any public function.

The check is case-insensitive and strips surrounding whitespace so that
variants such as ``"GROUND_TRUTH"``, ``"Ground_Truth"``, and ``" true_id "``
are all caught.
"""

FORBIDDEN_PARAM_NAMES: frozenset[str] = frozenset(FORBIDDEN_COLUMN_NAMES)
"""Parameter names that must not appear in any public SHADOWLINK function.

Identical to ``FORBIDDEN_COLUMN_NAMES``.  Defined separately so the
signature-inspection test can import the canonical set without circular
imports.
"""


# ---------------------------------------------------------------------------
# Public validators
# ---------------------------------------------------------------------------


def validate_no_forbidden_columns(df: pd.DataFrame) -> None:
    """Raise ``ValidationError`` if *df* contains any forbidden column name.

    The check is applied to the **original** column names after stripping
    leading/trailing whitespace and converting to lower-case.  It does not
    rely on ``normalize_column_name`` to avoid a circular dependency, but
    applies the same strip-then-lower logic.

    Parameters
    ----------
    df:
        DataFrame to inspect.  The DataFrame is not modified.

    Raises
    ------
    ValidationError
        If one or more column names match a forbidden name (case-insensitive).
        The error message lists every violation and instructs the caller to
        remove those columns before passing the DataFrame to SHADOWLINK.

    Examples
    --------
    >>> import pandas as pd
    >>> validate_no_forbidden_columns(pd.DataFrame({"age": [1], "city": ["X"]}))
    >>> # no exception raised

    >>> validate_no_forbidden_columns(pd.DataFrame({"ground_truth": [1]}))
    ValidationError: Input DataFrame contains forbidden column name(s): ...
    """
    normalised: set[str] = {str(col).strip().lower() for col in df.columns}
    violations: set[str] = normalised & FORBIDDEN_COLUMN_NAMES
    if violations:
        sorted_v = sorted(violations)
        raise ValidationError(
            f"Input DataFrame contains forbidden column name(s): {sorted_v}. "
            "SHADOWLINK does not accept ground-truth identity columns. "
            "Remove these columns before calling any SHADOWLINK function. "
            "See docs/decisions/forbidden_columns.md for the rationale."
        )


def validate_no_duplicate_columns(df: pd.DataFrame) -> None:
    """Raise ``ValidationError`` if *df* has duplicate column names.

    Parameters
    ----------
    df:
        DataFrame to inspect.

    Raises
    ------
    ValidationError
        If any column name appears more than once.
    """
    seen: set[str] = set()
    duplicates: list[str] = []
    for col in df.columns:
        col_str = str(col)
        if col_str in seen:
            duplicates.append(col_str)
        seen.add(col_str)
    if duplicates:
        dups_sorted = sorted(set(duplicates))
        raise ValidationError(
            f"Input DataFrame contains duplicate column name(s): {dups_sorted}. "
            "Rename or drop duplicate columns before calling SHADOWLINK functions."
        )


def validate_has_columns(df: pd.DataFrame) -> None:
    """Raise ``ValidationError`` if *df* has zero columns.

    Parameters
    ----------
    df:
        DataFrame to inspect.

    Raises
    ------
    ValidationError
        If the DataFrame has no columns at all.
    """
    if len(df.columns) == 0:
        raise ValidationError(
            "Input DataFrame has zero columns. "
            "Provide a DataFrame with at least one column."
        )


def validate_hashable_values(df: pd.DataFrame) -> None:
    """Raise ``ValidationError`` if *df* contains unhashable cell values.

    Unhashable values (e.g. lists, dicts, sets stored in cells) prevent
    grouping operations such as equivalence-class construction.

    Parameters
    ----------
    df:
        DataFrame to inspect.

    Raises
    ------
    ValidationError
        On the first column found to contain an unhashable value.
    """
    for col in df.columns:
        try:
            df[col].apply(hash)
        except TypeError as exc:
            raise ValidationError(
                f"Column '{col}' contains unhashable value(s): {exc}. "
                "Replace list/dict/set cell values with hashable scalar types "
                "before calling SHADOWLINK functions."
            ) from exc
