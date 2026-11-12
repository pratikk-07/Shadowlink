"""Synthetic Data Generator package for SHADOWLINK."""

from shadowlink.generator.generator import (
    generate_synthetic_bundle,
    report_abc,
    wide_release,
)
from shadowlink.generator.io import load_bundle, write_bundle
from shadowlink.generator.models import (
    DatasetSpec,
    GeneratedBundle,
    GeneratorConfig,
    TimestampWindow,
)

__all__ = [
    "DatasetSpec",
    "GeneratedBundle",
    "GeneratorConfig",
    "TimestampWindow",
    "generate_synthetic_bundle",
    "load_bundle",
    "report_abc",
    "wide_release",
    "write_bundle",
]

