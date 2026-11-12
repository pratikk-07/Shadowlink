"""Multi-dataset entity clustering with from-scratch disjoint-set (Union-Find)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import pandas as pd


class UnionFind:
    """Disjoint-set data structure with path compression and union by size."""

    def __init__(self) -> None:
        self.parent: dict[Any, Any] = {}
        self.size: dict[Any, int] = {}

    def make_set(self, x: Any) -> None:
        if x not in self.parent:
            self.parent[x] = x
            self.size[x] = 1

    def find(self, x: Any) -> Any:
        self.make_set(x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]

        # Path compression
        curr = x
        while curr != root:
            nxt = self.parent[curr]
            self.parent[curr] = root
            curr = nxt

        return root

    def union(self, x: Any, y: Any) -> None:
        root_x = self.find(x)
        root_y = self.find(y)
        if root_x == root_y:
            return

        # Union by size
        if self.size[root_x] < self.size[root_y]:
            root_x, root_y = root_y, root_x

        self.parent[root_y] = root_x
        self.size[root_x] += self.size[root_y]


@dataclass(frozen=True)
class ClusterResult:
    """Clustering outcome across multiple linked datasets."""

    clusters: list[list[tuple[str, str]]]
    cluster_sizes: list[int]
    has_intra_dataset_collision: bool
    colliding_clusters_count: int


def cluster_records(
    matched_pairs_list: list[pd.DataFrame],
    all_dataset_records: dict[str, list[str]] | None = None,
) -> ClusterResult:
    """Cluster records across pairwise linkage matches using Union-Find.

    Parameters
    ----------
    matched_pairs_list:
        List of scored candidate pair DataFrames with decision == 'match'.
    all_dataset_records:
        Optional mapping of dataset_name -> list of record_ids to include singletons.
    """
    uf = UnionFind()

    # Register all known records
    if all_dataset_records:
        for ds_name, rec_ids in all_dataset_records.items():
            for r_id in rec_ids:
                uf.make_set((ds_name, str(r_id)))

    # Process match decisions
    for df in matched_pairs_list:
        if df.empty:
            continue
        matches = df[df["decision"] == "match"]
        for _, row in matches.iterrows():
            node1 = (str(row["left_dataset"]), str(row["left_id"]))
            node2 = (str(row["right_dataset"]), str(row["right_id"]))
            uf.make_set(node1)
            uf.make_set(node2)
            uf.union(node1, node2)

    # Group records by root
    groups: dict[Any, list[tuple[str, str]]] = defaultdict(list)
    for node in uf.parent:
        root = uf.find(node)
        groups[root].append(node)

    cluster_list = list(groups.values())
    cluster_sizes = [len(c) for c in cluster_list]

    colliding_count = 0
    for c in cluster_list:
        datasets_in_cluster = [ds for ds, _ in c]
        if len(datasets_in_cluster) != len(set(datasets_in_cluster)):
            colliding_count += 1

    return ClusterResult(
        clusters=cluster_list,
        cluster_sizes=cluster_sizes,
        has_intra_dataset_collision=colliding_count > 0,
        colliding_clusters_count=colliding_count,
    )

