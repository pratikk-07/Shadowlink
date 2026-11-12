"""End-to-end pipeline connecting all SHADOWLINK modules."""

from shadowlink.pipeline.models import PipelineConfig, PipelineReport
from shadowlink.pipeline.runner import PipelineStageError, run_pipeline

__all__ = [
    "PipelineConfig",
    "PipelineReport",
    "PipelineStageError",
    "run_pipeline",
]

