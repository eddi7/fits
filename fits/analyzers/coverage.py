"""Coverage analysis artifact builders."""
from __future__ import annotations

import csv
import pathlib
from typing import Iterable, Iterator

from ..artifacts import CsvArtifact, build_artifact_name
from ..config import RunContext


COVERAGE_RESULTS_TABLE = "coverage_results"
LCOV_PATH_PREFIX = "foundation/graphic/graphic_2d_ext/ddgr/"
MODULE_MAPPING_FILE = "coverage_directory_module_owner_mapping.csv"


def _resolve_info_path(context: RunContext) -> pathlib.Path:
    """Return the lcov .info file to process based on CLI inputs."""

    if context.info_path:
        if not context.info_path.exists():
            raise FileNotFoundError(f"Coverage info not found at {context.info_path}")
        return context.info_path

    candidates = sorted(pathlib.Path.cwd().glob("*.info"))
    if not candidates:
        raise FileNotFoundError(
            "No .info files found in the current directory. Provide --info-path to choose one explicitly."
        )
    if len(candidates) > 1:
        joined = ", ".join(str(path) for path in candidates)
        raise ValueError(
            f"Multiple .info files found: {joined}. Provide --info-path to select one."
        )

    chosen = candidates[0].resolve()
    print(f"Using coverage info file: {chosen}")
    return chosen


def _split_directory_and_filename(sf_path: str) -> tuple[str, str]:
    """Split an lcov SF path into directory and filename parts."""

    normalized = sf_path.replace("\\", "/")
    idx = normalized.find(LCOV_PATH_PREFIX)
    trimmed = normalized[idx + len(LCOV_PATH_PREFIX) :] if idx != -1 else normalized
    parts = [part for part in trimmed.split("/") if part]

    if not parts:
        return "", ""
    if len(parts) == 1:
        return "", parts[0]

    return "/".join(parts[:-1]), parts[-1]


def _parse_lcov(info_path: pathlib.Path) -> list[dict[str, int | str]]:
    """Parse an lcov .info file into per-source coverage metrics."""

    files: list[dict[str, int | str]] = []
    current: dict[str, object] | None = None

    def finalize_current() -> None:
        nonlocal current
        if not current:
            return

        if current["lines_total"] == 0:
            current["lines_total"] = current["lines_total_da"]
        if current["lines_hit"] == 0:
            current["lines_hit"] = current["lines_hit_da"]

        if current["functions_total"] == 0:
            current["functions_total"] = len(current["fn_names"])
        if current["functions_hit"] == 0:
            current["functions_hit"] = len(current["fn_hit"])

        directory, file_name = _split_directory_and_filename(str(current["sf"]))
        current["directory"] = directory
        current["file_name"] = file_name

        current.pop("fn_names", None)
        current.pop("fn_hit", None)
        current.pop("lines_total_da", None)
        current.pop("lines_hit_da", None)
        current.pop("sf", None)

        files.append(current)  # type: ignore[arg-type]
        current = None

    with info_path.open("r", encoding="utf-8", errors="ignore") as info_file:
        for raw in info_file:
            line = raw.strip()
            if not line:
                continue

            if line.startswith("SF:"):
                finalize_current()
                current = {
                    "sf": line[3:],
                    "lines_total": 0,
                    "lines_hit": 0,
                    "lines_total_da": 0,
                    "lines_hit_da": 0,
                    "functions_total": 0,
                    "functions_hit": 0,
                    "fn_names": set(),
                    "fn_hit": set(),
                    "branches_total": 0,
                    "branches_hit": 0,
                }
                continue

            if current is None:
                continue

            if line.startswith("DA:"):
                _, rest = line.split(":", 1)
                parts = rest.split(",")
                if len(parts) >= 2:
                    count = int(parts[1])
                    current["lines_total_da"] += 1
                    if count > 0:
                        current["lines_hit_da"] += 1
                continue

            if line.startswith("LH:"):
                _, value = line.split(":", 1)
                current["lines_hit"] = int(value)
                continue

            if line.startswith("LF:"):
                _, value = line.split(":", 1)
                current["lines_total"] = int(value)
                continue

            if line.startswith("FN:"):
                _, rest = line.split(":", 1)
                parts = rest.split(",", 1)
                if len(parts) == 2:
                    current["fn_names"].add(parts[1])
                continue

            if line.startswith("FNDA:"):
                _, rest = line.split(":", 1)
                parts = rest.split(",", 1)
                if len(parts) == 2:
                    count_str, name = parts
                    current["fn_names"].add(name)
                    if int(count_str) > 0:
                        current["fn_hit"].add(name)
                continue

            if line.startswith("FNF:"):
                _, value = line.split(":", 1)
                if current["functions_total"] == 0:
                    current["functions_total"] = int(value)
                continue

            if line.startswith("FNH:"):
                _, value = line.split(":", 1)
                if current["functions_hit"] == 0:
                    current["functions_hit"] = int(value)
                continue

            if line.startswith("BRDA:"):
                _, rest = line.split(":", 1)
                parts = rest.split(",")
                if len(parts) == 4:
                    taken = parts[3]
                    current["branches_total"] += 1
                    if taken != "-" and int(taken) > 0:
                        current["branches_hit"] += 1
                continue

            if line.startswith("BRF:"):
                _, value = line.split(":", 1)
                if current["branches_total"] == 0:
                    current["branches_total"] = int(value)
                continue

            if line.startswith("BRH:"):
                _, value = line.split(":", 1)
                if current["branches_hit"] == 0:
                    current["branches_hit"] = int(value)
                continue

            if line == "end_of_record":
                finalize_current()

    finalize_current()
    return files


def _load_module_mapping(config_dir: pathlib.Path) -> list[tuple[str, str, str | None]]:
    """Load directory-to-module/owner mapping from the FITS config repo."""

    mapping_path = config_dir / MODULE_MAPPING_FILE
    if not mapping_path.exists():
        raise FileNotFoundError(
            f"Coverage module mapping not found at {mapping_path}. Ensure git-clone-configs fetched FITS data."
        )

    with mapping_path.open(newline="", encoding="utf-8-sig") as mapping_file:
        reader = csv.DictReader(mapping_file)
        required = {"directory", "module", "owner"}
        if not reader.fieldnames or required - set(reader.fieldnames):
            raise ValueError(
                f"{MODULE_MAPPING_FILE} must contain directory, module, and owner columns"
            )

        mapping: list[tuple[str, str, str | None]] = []
        for row in reader:
            directory = (row.get("directory") or "").strip().strip("/")
            module = (row.get("module") or "").strip()
            owner = (row.get("owner") or "").strip() or None
            if not directory or not module:
                continue
            mapping.append((directory.replace("\\", "/"), module, owner))

    return mapping


def _module_owner_for_directory(
    directory: str, mapping: list[tuple[str, str, str | None]]
) -> tuple[str | None, str | None]:
    """Return the closest module/owner mapping for a directory."""

    normalized = directory.strip("/").replace("\\", "/")
    best: tuple[str, str, str | None] | None = None

    for mapped_dir, module, owner in mapping:
        mapped_normalized = mapped_dir.strip("/")
        if normalized == mapped_normalized or normalized.startswith(mapped_normalized + "/"):
            if best is None or len(mapped_normalized) > len(best[0]):
                best = (mapped_normalized, module, owner)

    if best:
        return best[1], best[2]

    return None, None


def _build_rows(context: RunContext) -> Iterator[dict[str, str | int | None]]:
    """Yield coverage rows enriched with module and owner metadata."""

    info_path = _resolve_info_path(context)
    config_dir = pathlib.Path.cwd() / "FITS"
    mapping = _load_module_mapping(config_dir)
    parsed = _parse_lcov(info_path)

    for record in parsed:
        module, owner = _module_owner_for_directory(str(record["directory"]), mapping)
        yield {
            "exec_id": context.exec_id,
            "directory": record["directory"],
            "file_name": record["file_name"],
            "lines_hit": record["lines_hit"],
            "lines_total": record["lines_total"],
            "functions_hit": record["functions_hit"],
            "functions_total": record["functions_total"],
            "branches_hit": record["branches_hit"],
            "branches_total": record["branches_total"],
            "module": module,
            "owner": owner,
        }


def build_coverage_artifacts(context: RunContext) -> Iterable[CsvArtifact]:
    """Construct coverage CSV artifacts for upload."""

    yield CsvArtifact(
        name=build_artifact_name(context.db_config.database, COVERAGE_RESULTS_TABLE),
        headers=[
            "exec_id",
            "directory",
            "file_name",
            "lines_hit",
            "lines_total",
            "functions_hit",
            "functions_total",
            "branches_hit",
            "branches_total",
            "module",
            "owner",
        ],
        rows=_build_rows(context),
        table=COVERAGE_RESULTS_TABLE,
    )
