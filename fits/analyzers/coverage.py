"""Coverage analysis artifact builders."""
from __future__ import annotations

from typing import Iterable

from ..artifacts import CsvArtifact
from ..config import RunContext


def build_coverage_artifacts(context: RunContext) -> Iterable[CsvArtifact]:
    """Construct a simple CSV artifact for coverage mode."""
    yield CsvArtifact(
        name=f"coverage_summary_{context.exe_id}.csv",
        headers=["exe_id", "device", "suite", "percent"],
        rows=[
            {
                "exe_id": context.exe_id,
                "device": context.device,
                "suite": "sample_suite",
                "percent": 0.0,
            },
        ],
        table="coverage_summary",
    )
