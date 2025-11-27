"""DTK analysis artifact builders."""
from __future__ import annotations

import pathlib
from typing import Iterable, Iterator

from ..artifacts import CsvArtifact, build_artifact_name
from ..config import RunContext


DTK_RESULTS_TABLE = "dtk_results"


def _results_path(context: RunContext) -> pathlib.Path:
    """Return the expected path for the DTK results text file."""

    default_path = context.exec_dir.parent / "result" / "output.txt"
    if not default_path.exists():
        raise FileNotFoundError(f"DTK results not found at {default_path}")

    return default_path


def _parse_result_line(line: str) -> tuple[str, str]:
    """Parse a single DTK result line of the form ``<case>#<result>``."""

    trimmed = line.strip()
    if not trimmed:
        raise ValueError("Encountered empty DTK result line")

    if trimmed.count("#") != 1:
        raise ValueError(f"Invalid DTK result format: {trimmed}")

    case, result = trimmed.split("#", 1)
    if not case or not result:
        raise ValueError(f"Invalid DTK result format: {trimmed}")

    return case, result


def _read_results(context: RunContext) -> Iterator[dict[str, str]]:
    """Yield parsed DTK results from the execution directory."""

    path = _results_path(context)
    with path.open() as results_file:
        for line in results_file:
            case, result = _parse_result_line(line)
            yield {"exec_id": context.exec_id, "case": case, "result": result}


def build_dtk_artifacts(context: RunContext) -> Iterable[CsvArtifact]:
    """Construct a DTK CSV with execution id, case name, and result."""

    yield CsvArtifact(
        name=build_artifact_name(context.db_config.database, DTK_RESULTS_TABLE),
        headers=["exec_id", "case", "result"],
        rows=_read_results(context),
        table=DTK_RESULTS_TABLE,
    )
