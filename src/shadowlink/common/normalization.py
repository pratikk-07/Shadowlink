"""Column-name normalisation for SHADOWLINK.

The normalisation rule applied throughout the platform:

    1. Strip leading and trailing whitespace (including tabs, newlines).
    2. Convert to lower-case.
    3. Collapse any run of internal whitespace to a single ASCII space.

This ensures that raw column names from real-world CSV files such as
``" Age "``, ``"AGE"``, and ``"age"`` all map to the canonical form ``"age"``,
enabling cross-dataset attribute matching without manual renaming.

The normalised name is used **internally** for comparisons and in profile
output.  The *original* column name is always preserved in
``ColumnProfile.name`` so that the caller can trace back to the source.
"""

from __future__ import annotations

import re


def normalize_column_name(name: str) -> str:
    """Normalise a CSV column name for cross-dataset comparison.

    Steps applied, in order:

    1. Strip leading / trailing whitespace (space, tab, newline, carriage-return).
    2. Convert to lower-case.
    3. Collapse any sequence of internal whitespace characters to a single
       ASCII space ``" "``.

    Parameters
    ----------
    name:
        Raw column name, possibly with surrounding spaces, mixed case, or
        multiple internal whitespace characters.

    Returns
    -------
    str
        Normalised column name.  An all-whitespace input returns ``""``.

    Examples
    --------
    >>> normalize_column_name(" Age ")
    'age'
    >>> normalize_column_name("CITY")
    'city'
    >>> normalize_column_name("  First   Name  ")
    'first name'
    >>> normalize_column_name("TIMESTAMP")
    'timestamp'
    """
    stripped: str = name.strip()
    lowered: str = stripped.lower()
    collapsed: str = re.sub(r"\s+", " ", lowered)
    return collapsed
