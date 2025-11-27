"""Coverage analysis artifact builders."""
from __future__ import annotations

from typing import Iterable

from ..artifacts import CsvArtifact, build_artifact_name
from ..config import RunContext


COVERAGE_SUMMARY_TABLE = "coverage_summary"


def build_coverage_artifacts(context: RunContext) -> Iterable[CsvArtifact]:
    """Construct a simple CSV artifact for coverage mode."""
    yield CsvArtifact(
        name=build_artifact_name(context.db_config.database, COVERAGE_SUMMARY_TABLE),
        headers=["exec_id", "device", "suite", "percent"],
        rows=[
            {
                "exec_id": context.exec_id,
                "device": context.device,
                "suite": "sample_suite",
                "percent": 0.0,
            },
        ],
        table=COVERAGE_SUMMARY_TABLE,
    )
