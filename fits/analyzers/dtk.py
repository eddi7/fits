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


def _baseline_path(context: RunContext) -> pathlib.Path:
    """Return the expected path for the DTK baseline text file."""

    default_path = context.exec_dir.parent / "standard_fully.txt"
    if not default_path.exists():
        raise FileNotFoundError(f"DTK baseline not found at {default_path}")

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
    """Yield parsed DTK results with optional baseline values.

    Case names ending with ``.jpg`` have the suffix removed so image artifacts
    are normalized to their associated case names.
    """

    results_path = _results_path(context)
    baseline_path = _baseline_path(context)

    def _read_cases(path: pathlib.Path) -> list[tuple[str, str]]:
        cases: list[tuple[str, str]] = []
        with path.open() as results_file:
            for line in results_file:
                case, value = _parse_result_line(line)
                if case.lower().endswith(".jpg"):
                    case = case[:-4]
                cases.append((case, value))
        return cases

    results = _read_cases(results_path)
    baselines = _read_cases(baseline_path)

    baseline_lookup = {case: value for case, value in baselines}
    seen: set[str] = set()

    for case, result in results:
        seen.add(case)
        yield {
            "exec_id": context.exec_id,
            "case": case,
            "result": result,
            "baseline": baseline_lookup.get(case),
        }

    for case, baseline in baselines:
        if case in seen:
            continue
        yield {
            "exec_id": context.exec_id,
            "case": case,
            "result": None,
            "baseline": baseline,
        }


def build_dtk_artifacts(context: RunContext) -> Iterable[CsvArtifact]:
    """Construct a DTK CSV with execution id, case name, and result."""

    yield CsvArtifact(
        name=build_artifact_name(context.db_config.database, DTK_RESULTS_TABLE),
        headers=["exec_id", "case", "result", "baseline"],
        rows=_read_results(context),
        table=DTK_RESULTS_TABLE,
    )
