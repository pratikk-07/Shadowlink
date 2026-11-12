"""Record Linkage package for SHADOWLINK."""

from shadowlink.linkage.blocking import (
    BlockingPass,
    BlockingReport,
    generate_candidate_pairs,
)
from shadowlink.linkage.clustering import ClusterResult, UnionFind, cluster_records
from shadowlink.linkage.comparators import (
    exact_comparator,
    jaro_similarity,
    jaro_winkler_similarity,
    levenshtein_distance,
    levenshtein_similarity,
    numeric_comparator,
    time_comparator,
)
from shadowlink.linkage.fellegi_sunter import fellegi_sunter_linkage
from shadowlink.linkage.methods import (
    best_match_per_record,
    deterministic_linkage,
    similarity_linkage,
)
from shadowlink.linkage.models import AttributeComparatorSpec, FellegiSunterParams
from shadowlink.linkage.preprocessing import (
    parse_datetime_safe,
    preprocess_linkage_frame,
    standardize_text,
)

__all__ = [
    "AttributeComparatorSpec",
    "BlockingPass",
    "BlockingReport",
    "ClusterResult",
    "FellegiSunterParams",
    "UnionFind",
    "best_match_per_record",
    "cluster_records",
    "deterministic_linkage",
    "exact_comparator",
    "fellegi_sunter_linkage",
    "generate_candidate_pairs",
    "jaro_similarity",
    "jaro_winkler_similarity",
    "levenshtein_distance",
    "levenshtein_similarity",
    "numeric_comparator",
    "parse_datetime_safe",
    "preprocess_linkage_frame",
    "similarity_linkage",
    "standardize_text",
    "time_comparator",
]
