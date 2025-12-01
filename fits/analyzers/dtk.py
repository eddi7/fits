"""DTK analysis artifact builders."""
from __future__ import annotations

import csv
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


def _parse_result_line(line: str) -> tuple[str, str | None]:
    """Parse a single DTK result line of the form ``<case>#<result>``.

    Empty result fields are interpreted as ``None`` so they can be inserted as
    ``NULL`` values in the database.
    """

    trimmed = line.strip()
    if not trimmed:
        raise ValueError("Encountered empty DTK result line")

    if trimmed.count("#") != 1:
        raise ValueError(f"Invalid DTK result format: {trimmed}")

    case, result = trimmed.split("#", 1)
    if not case:
        raise ValueError(f"Invalid DTK result format: {trimmed}")

    if result == "":
        return case, None

    return case, result


def _load_mapping(
    path: pathlib.Path, key_field: str, value_field: str
) -> dict[str, str]:
    mapping: dict[str, str] = {}

    try:
        with path.open(newline="") as mapping_file:
            reader = csv.DictReader(mapping_file)
            if not reader.fieldnames or {
                key_field,
                value_field,
            } - set(reader.fieldnames):
                return mapping

            for row in reader:
                key = (row.get(key_field) or "").strip()
                value = (row.get(value_field) or "").strip()
                if not key or not value:
                    continue
                mapping[key] = value
    except FileNotFoundError:
        return mapping

    return mapping


def _module_for_case(case: str, case_to_module: dict[str, str]) -> str | None:
    best_match: str | None = None
    best_length = 0

    for casename, module in case_to_module.items():
        if not case.startswith(casename):
            continue

        if len(casename) > best_length:
            best_match = module
            best_length = len(casename)

    return best_match


def _read_results(
    context: RunContext,
    case_to_module: dict[str, str],
    module_to_owner: dict[str, str],
) -> Iterator[dict[str, str | None]]:
    """Yield parsed DTK results with optional baseline values.

    Case names ending with ``.jpg`` have the suffix removed so image artifacts
    are normalized to their associated case names.
    """

    results_path = _results_path(context)
    baseline_path = _baseline_path(context)

    def _read_cases(path: pathlib.Path) -> list[tuple[str, str | None]]:
        cases: list[tuple[str, str | None]] = []
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
        module = _module_for_case(case, case_to_module)
        yield {
            "exec_id": context.exec_id,
            "case": case,
            "module": module,
            "owner": module_to_owner.get(module) if module else None,
            "result": result,
            "baseline": baseline_lookup.get(case),
        }

    for case, baseline in baselines:
        if case in seen:
            continue
        module = _module_for_case(case, case_to_module)
        yield {
            "exec_id": context.exec_id,
            "case": case,
            "module": module,
            "owner": module_to_owner.get(module) if module else None,
            "result": None,
            "baseline": baseline,
        }


def build_dtk_artifacts(context: RunContext) -> Iterable[CsvArtifact]:
    """Construct a DTK CSV with execution id, case name, and result."""

    config_dir = pathlib.Path.cwd() / "FITS"
    case_to_module = _load_mapping(config_dir / "casename-to-module.csv", "casename", "module")
    module_to_owner = _load_mapping(config_dir / "module-to-owner.csv", "module", "owner")

    yield CsvArtifact(
        name=build_artifact_name(context.db_config.database, DTK_RESULTS_TABLE),
        headers=["exec_id", "case", "module", "owner", "result", "baseline"],
        rows=_read_results(context, case_to_module, module_to_owner),
        table=DTK_RESULTS_TABLE,
    )
