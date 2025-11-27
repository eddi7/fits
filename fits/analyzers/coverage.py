"""Coverage analysis artifact builders."""
from __future__ import annotations

from typing import Iterable

from ..artifacts import CsvArtifact
from ..config import RunContext


def build_coverage_artifacts(context: RunContext) -> Iterable[CsvArtifact]:
    """Construct a simple CSV artifact for coverage mode."""
    yield CsvArtifact(
        name=f"fitsdb-{context.exec_id}.coverage_summary.csv",
        headers=["exec_id", "device", "suite", "percent"],
        rows=[
            {
                "exec_id": context.exec_id,
                "device": context.device,
                "suite": "sample_suite",
                "percent": 0.0,
            },
        ],
        table="coverage_summary",
    )
