"""From-scratch attribute comparison and string similarity algorithms."""

from __future__ import annotations

import pandas as pd

from shadowlink.linkage.preprocessing import parse_datetime_safe


def _is_none_or_na(val: object) -> bool:
    if val is None:
        return True
    try:
        return bool(pd.isna(val))  # type: ignore[call-overload,arg-type]
    except Exception:
        return False


def exact_comparator(v1: object, v2: object) -> float | None:
    """Exact equality comparator.

    Returns 1.0 on agreement, 0.0 on disagreement, None if either is missing.
    """
    if _is_none_or_na(v1) or _is_none_or_na(v2):
        return None
    if isinstance(v1, str) and isinstance(v2, str):
        return 1.0 if v1.strip().lower() == v2.strip().lower() else 0.0
    return 1.0 if v1 == v2 else 0.0


def numeric_comparator(v1: object, v2: object, tolerance: float = 0.0) -> float | None:
    """Bounded numeric difference comparator.

    Returns similarity in [0.0, 1.0] scaling linearly to 0.0 at tolerance,
    or None if either value is missing/unparseable.
    """
    if _is_none_or_na(v1) or _is_none_or_na(v2):
        return None
    try:
        n1 = float(v1)  # type: ignore[arg-type]
        n2 = float(v2)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return None

    diff = abs(n1 - n2)
    if tolerance <= 0.0:
        return 1.0 if diff == 0.0 else 0.0
    if diff >= tolerance:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (diff / tolerance)))


def time_comparator(
    v1: object, v2: object, window_minutes: float = 0.0
) -> float | None:
    """Temporal proximity comparator.

    Returns similarity in [0.0, 1.0] scaling linearly within the window,
    or None if either value cannot be parsed.
    """
    if _is_none_or_na(v1) or _is_none_or_na(v2):
        return None
    dt1 = parse_datetime_safe(v1)
    dt2 = parse_datetime_safe(v2)
    if dt1 is None or dt2 is None:
        return None

    diff_mins = abs((dt1 - dt2).total_seconds()) / 60.0
    if window_minutes <= 0.0:
        return 1.0 if diff_mins == 0.0 else 0.0
    if diff_mins >= window_minutes:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (diff_mins / window_minutes)))


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance from scratch."""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        c1 = s1[i - 1]
        for j in range(1, n + 1):
            c2 = s2[j - 1]
            cost = 0 if c1 == c2 else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,  # deletion
                dp[i][j - 1] + 1,  # insertion
                dp[i - 1][j - 1] + cost,  # substitution
            )

    return dp[m][n]


def levenshtein_similarity(s1: object, s2: object) -> float | None:
    """Normalized Levenshtein similarity: 1 - dist / max_len.

    Both empty strings return 1.0. Returns None if either is missing.
    """
    if _is_none_or_na(s1) or _is_none_or_na(s2):
        return None
    str1 = str(s1)
    str2 = str(s2)
    if not str1 and not str2:
        return 1.0
    max_len = max(len(str1), len(str2))
    dist = levenshtein_distance(str1, str2)
    return max(0.0, min(1.0, 1.0 - (dist / max_len)))


def jaro_similarity(s1: object, s2: object) -> float | None:
    """Compute Jaro string similarity from scratch.

    Returns similarity in [0.0, 1.0], or None if either string is missing.
    """
    if _is_none_or_na(s1) or _is_none_or_na(s2):
        return None
    str1 = str(s1)
    str2 = str(s2)
    if str1 == str2:
        return 1.0

    len1, len2 = len(str1), len(str2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_dist = max(len1, len2) // 2 - 1
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0

    for i in range(len1):
        start = max(0, i - match_dist)
        end = min(i + match_dist + 1, len2)
        for j in range(start, end):
            if not s2_matches[j] and str1[i] == str2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    k = 0
    transpositions = 0
    for i in range(len1):
        if s1_matches[i]:
            while not s2_matches[k]:
                k += 1
            if str1[i] != str2[k]:
                transpositions += 1
            k += 1

    t = transpositions / 2.0
    score = (matches / len1 + matches / len2 + (matches - t) / matches) / 3.0
    return max(0.0, min(1.0, float(score)))


def jaro_winkler_similarity(
    s1: object,
    s2: object,
    p: float = 0.1,
    max_p: int = 4,
) -> float | None:
    """Compute Jaro-Winkler string similarity from scratch.

    Standard scaling parameter p=0.1, max prefix length 4.
    """
    if _is_none_or_na(s1) or _is_none_or_na(s2):
        return None
    j = jaro_similarity(s1, s2)
    if j is None:
        return None

    str1 = str(s1)
    str2 = str(s2)
    prefix = 0
    for c1, c2 in zip(str1, str2):
        if c1 == c2:
            prefix += 1
            if prefix == max_p:
                break
        else:
            break

    jw = j + prefix * p * (1.0 - j)
    return max(0.0, min(1.0, float(jw)))
