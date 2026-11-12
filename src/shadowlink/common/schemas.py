"""Shared schemas and contracts for candidate risk and attacker simulation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AttackerStepSummary:
    """Summary of a single step in an attacker background knowledge simulation.

    Consumed from teammate's Attacker Simulator module.
    """

    step: int
    known_attributes: list[str]
    candidate_count: int
