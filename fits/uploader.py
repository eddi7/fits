"""Upload helpers for CSV artifacts."""
from __future__ import annotations

import csv
import importlib
import pathlib
import random
from datetime import datetime
from typing import Iterable

from .config import DatabaseConfig


class UploadError(RuntimeError):
    """Raised when a CSV upload fails."""


def _mode_task_id(build_type: str) -> str:
    mapping = {"dtk": "01", "coverage": "02"}
    if build_type not in mapping:
        raise ValueError(f"Unknown build_type '{build_type}' for exec_id generation")
    return mapping[build_type]


def generate_exec_id(build_type: str, *, test: bool = False) -> str:
    """Build an 18-digit execution identifier for uploads."""

    now = datetime.now()
    random_suffix = f"{random.randint(0, 99):02d}"
    task_id = _mode_task_id(build_type)
    prefix = "9999" if test else now.strftime("%Y")
    timestamp = now.strftime("%m%d%H%M%S")
    return f"{prefix}{timestamp}{random_suffix}{task_id}"


def _read_rows(path: pathlib.Path):
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            yield {
                key: None if value == "" else value
                for key, value in row.items()
            }


def _connect(config: DatabaseConfig):
    spec = importlib.util.find_spec("mysql.connector")
    if spec is None:  # pragma: no cover - import guard
        raise UploadError("mysql-connector-python is not installed")

    mysql = importlib.import_module("mysql.connector")

    return mysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
    ), mysql


def upload_csv(path: pathlib.Path, table: str, config: DatabaseConfig) -> int:
    connection, mysql = _connect(config)

    rows = list(_read_rows(path))
    if not rows:
        connection.close()
        return 0

    placeholders = ",".join(["%s"] * len(rows[0]))
    columns = ",".join(f"`{column}`" for column in rows[0].keys())
    sql = f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})"

    try:
        with connection.cursor() as cursor:
            cursor.executemany(sql, [tuple(row.values()) for row in rows])
        connection.commit()
    except mysql.Error as exc:  # pragma: no cover - runtime dependent
        raise UploadError(str(exc))
    finally:
        connection.close()

    return len(rows)


def upload_many(paths: Iterable[tuple[pathlib.Path, str]], config: DatabaseConfig) -> int:
    """Upload multiple CSV files and return the total inserted row count."""
    total = 0
    for path, table in paths:
        total += upload_csv(path, table, config)
    return total


def record_execution(
    exec_id: str,
    build_type: str,
    archive_dir: pathlib.Path,
    config: DatabaseConfig,
    *,
    device_type: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    """Insert a single execution row into the executions table."""

    connection, _ = _connect(config)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO executions (exec_id, build_type, archive_dir, device_type, started_at, completed_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    int(exec_id),
                    build_type,
                    str(archive_dir),
                    device_type,
                    started_at,
                    completed_at,
                ),
            )
        connection.commit()
    except Exception as exc:  # pragma: no cover - runtime dependent
        raise UploadError(str(exc))
    finally:
        connection.close()


def ensure_ready(paths: Iterable[tuple[pathlib.Path, str]]) -> None:
    """Ensure artifact files exist and are non-empty before upload."""

    missing = [path for path, _ in paths if not path.exists() or path.stat().st_size == 0]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise UploadError(f"Artifacts not ready for upload: {joined}")


def upload_dtk(
    paths: Iterable[tuple[pathlib.Path, str]],
    config: DatabaseConfig,
    exec_id: str,
    archive_dir: pathlib.Path,
    *,
    device_type: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> int:
    """Upload DTK artifacts and record the execution."""

    ensure_ready(paths)
    record_execution(
        exec_id,
        "dtk",
        archive_dir,
        config,
        device_type=device_type,
        started_at=started_at,
        completed_at=completed_at,
    )
    return upload_many(paths, config)


def upload_coverage(
    paths: Iterable[tuple[pathlib.Path, str]],
    config: DatabaseConfig,
    exec_id: str,
    archive_dir: pathlib.Path,
    *,
    device_type: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> int:
    """Upload coverage artifacts and record the execution."""

    ensure_ready(paths)
    record_execution(
        exec_id,
        "coverage",
        archive_dir,
        config,
        device_type=device_type,
        started_at=started_at,
        completed_at=completed_at,
    )
    return upload_many(paths, config)
