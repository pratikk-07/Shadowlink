"""Unit tests for Phase 4 Linkage methods, FS hand oracles, and clustering."""

from __future__ import annotations

import pandas as pd
import pytest

from shadowlink.linkage.clustering import UnionFind, cluster_records
from shadowlink.linkage.fellegi_sunter import fellegi_sunter_linkage
from shadowlink.linkage.methods import (
    best_match_per_record,
    deterministic_linkage,
    similarity_linkage,
)
from shadowlink.linkage.models import AttributeComparatorSpec, FellegiSunterParams


class TestFellegiSunterHandOracle:
    """Exact test oracle from project specification.

    attribute 1 (m=0.9, u=0.2): agree log2(4.5)=2.169925, disagree -3.0
    attribute 2 (m=0.8, u=0.2): agree 2.0, disagree -2.0

    Pair outcomes:
    - agrees on 1, disagrees on 2: 0.169925
    - agrees on both: 4.169925
    - disagrees on both: -5.0
    - attribute 2 missing and attribute 1 agrees: 2.169925
    """

    def test_fellegi_sunter_oracle_scores(self) -> None:
        left = pd.DataFrame(
            {
                "record_id": ["L1", "L2", "L3", "L4"],
                "attr1": ["A", "A", "A", "A"],
                "attr2": ["B", "B", "B", "B"],
            }
        )
        right = pd.DataFrame(
            {
                "record_id": ["R1", "R2", "R3", "R4"],
                "attr1": ["A", "A", "X", "A"],
                "attr2": ["X", "B", "X", None],
            }
        )
        # Pairs:
        # L1-R1: agrees on 1, disagrees on 2 -> 2.169925 - 2.0 = 0.169925
        # L2-R2: agrees on both -> 2.169925 + 2.0 = 4.169925
        # L3-R3: disagrees on both -> -3.0 - 2.0 = -5.0
        # L4-R4: attr2 missing and attr1 agrees -> 2.169925 + 0.0 = 2.169925
        pairs = pd.DataFrame(
            {
                "left_id": ["L1", "L2", "L3", "L4"],
                "right_id": ["R1", "R2", "R3", "R4"],
            }
        )
        specs = [
            AttributeComparatorSpec(attribute="attr1", method="exact"),
            AttributeComparatorSpec(attribute="attr2", method="exact"),
        ]
        params = FellegiSunterParams(
            m_probabilities={"attr1": 0.9, "attr2": 0.8},
            u_probabilities={"attr1": 0.2, "attr2": 0.2},
        )

        res = fellegi_sunter_linkage(
            left, right, pairs, specs, params, lower_threshold=0.0, upper_threshold=3.0
        )

        scores = dict(zip(zip(res["left_id"], res["right_id"]), res["score"]))
        decisions = dict(zip(zip(res["left_id"], res["right_id"]), res["decision"]))

        assert scores[("L1", "R1")] == pytest.approx(0.169925, abs=1e-5)
        assert decisions[("L1", "R1")] == "possible"

        assert scores[("L2", "R2")] == pytest.approx(4.169925, abs=1e-5)
        assert decisions[("L2", "R2")] == "match"

        assert scores[("L3", "R3")] == pytest.approx(-5.0, abs=1e-5)
        assert decisions[("L3", "R3")] == "non_match"

        assert scores[("L4", "R4")] == pytest.approx(2.169925, abs=1e-5)
        assert decisions[("L4", "R4")] == "possible"


class TestLinkageMethodsAndTypoRobustness:
    def test_typo_robustness_similarity_vs_deterministic(self) -> None:
        """Kolkata vs Kolakta:

        Deterministic fails (exact match=0).
        Similarity with Jaro-Winkler succeeds with high similarity score (~0.96).
        """
        left = pd.DataFrame({"record_id": ["L1"], "city": ["Kolkata"]})
        right = pd.DataFrame({"record_id": ["R1"], "city": ["Kolakta"]})
        pairs = pd.DataFrame({"left_id": ["L1"], "right_id": ["R1"]})

        det_res = deterministic_linkage(left, right, pairs, attributes=["city"])
        assert det_res["decision"].iloc[0] == "non_match"
        assert det_res["score"].iloc[0] == 0.0

        sim_spec = [AttributeComparatorSpec(attribute="city", method="jaro_winkler")]
        sim_res = similarity_linkage(left, right, pairs, specs=sim_spec, threshold=0.85)
        assert sim_res["decision"].iloc[0] == "match"
        assert sim_res["score"].iloc[0] > 0.9


class TestBestMatchAndClustering:
    def test_best_match_per_record_ranking_and_ties(self) -> None:
        scored = pd.DataFrame(
            {
                "left_id": ["L1", "L1", "L1"],
                "right_id": ["R2", "R1", "R3"],
                "score": [0.9, 0.9, 0.5],
            }
        )
        ranked = best_match_per_record(scored)
        # R1 and R2 tie at 0.9 -> R1 wins tie-break (alphabetical order)
        assert ranked["right_id"].iloc[0] == "R1"
        assert ranked["rank"].iloc[0] == 1
        assert ranked["tie_group_size"].iloc[0] == 2

        assert ranked["right_id"].iloc[1] == "R2"
        assert ranked["rank"].iloc[1] == 2
        assert ranked["tie_group_size"].iloc[1] == 2

        assert ranked["right_id"].iloc[2] == "R3"
        assert ranked["rank"].iloc[2] == 3

    def test_union_find_and_clustering(self) -> None:
        uf = UnionFind()
        uf.union("A", "B")
        uf.union("B", "C")
        assert uf.find("A") == uf.find("C")

        matches = pd.DataFrame(
            {
                "left_dataset": ["A", "B"],
                "left_id": ["A-1", "B-1"],
                "right_dataset": ["B", "C"],
                "right_id": ["B-1", "C-1"],
                "decision": ["match", "match"],
            }
        )
        res = cluster_records([matches])
        assert len(res.clusters) == 1
        assert len(res.clusters[0]) == 3
        assert not res.has_intra_dataset_collision

    def test_clustering_intra_dataset_collision(self) -> None:
        """Two records from same dataset merged -> collision flagged."""
        matches = pd.DataFrame(
            {
                "left_dataset": ["A", "A"],
                "left_id": ["A-1", "A-2"],
                "right_dataset": ["B", "B"],
                "right_id": ["B-1", "B-1"],
                "decision": ["match", "match"],
            }
        )
        res = cluster_records([matches])
        assert res.has_intra_dataset_collision
        assert res.colliding_clusters_count == 1
