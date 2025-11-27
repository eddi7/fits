"""DTK analysis artifact builders."""
from __future__ import annotations

import random
from typing import Iterable

from ..artifacts import CsvArtifact
from ..config import RunContext


def _build_sample_rows(context: RunContext, count: int = 10):
    rng = random.Random(context.exe_id)
    for _ in range(count):
        case = f"Path_Clip_{rng.randint(1, 9)}_L{rng.randint(1, 5)}_{rng.randint(100, 999)}"
        yield {
            "exe_id": context.exe_id,
            "case": case,
            "result": f"{rng.random():.10f}",
        }


def build_dtk_artifacts(context: RunContext) -> Iterable[CsvArtifact]:
    """Construct a DTK CSV with execution id, case name, and result."""

    yield CsvArtifact(
        name=f"dtk_summary_{context.exe_id}.csv",
        headers=["exe_id", "case", "result"],
        rows=_build_sample_rows(context, count=12),
        table="dtk_summary",
    )
