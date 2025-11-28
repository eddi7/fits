"""Configuration helpers for the FITS CLI."""
from __future__ import annotations

import configparser
import os
import pathlib
from dataclasses import dataclass


CONFIG_ENV_VAR = "FITS_DB_CONFIG"
USER_CONFIG_PATH = pathlib.Path.home() / ".config" / "fits" / "db_config.ini"
PACKAGE_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / "config" / "db_config.ini"


@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class RunContext:
    exec_id: str
    device: str
    mode: str
    device_type: str | None
    exec_dir: pathlib.Path
    db_config: DatabaseConfig


def detect_device() -> str:
    """Return the hostname or a fallback device identifier."""
    return os.environ.get("DEVICE_NAME") or os.uname().nodename


def _load_from_path(candidate: pathlib.Path) -> DatabaseConfig:
    parser = configparser.ConfigParser()
    parser.read(candidate)

    if "mysql" not in parser:
        raise ValueError("Database config must contain a [mysql] section")

    mysql_cfg = parser["mysql"]
    try:
        port = int(mysql_cfg.get("port", "3306"))
    except ValueError as exc:
        raise ValueError("Database port must be an integer") from exc

    required_keys = ["host", "user", "password", "database"]
    missing = [key for key in required_keys if key not in mysql_cfg]
    if missing:
        raise ValueError(f"Missing MySQL config keys: {', '.join(missing)}")

    return DatabaseConfig(
        host=mysql_cfg["host"],
        port=port,
        user=mysql_cfg["user"],
        password=mysql_cfg["password"],
        database=mysql_cfg["database"],
    )


def load_db_config(path: pathlib.Path | None = None) -> DatabaseConfig:
    """Load database settings from an INI file.

    The file path is resolved via the FITS_DB_CONFIG environment variable or
    defaults to ``~/.config/fits/db_config.ini`` with a fallback to the
    repository's ``config/db_config.ini`` for development.
    """

    env_override = os.environ.get(CONFIG_ENV_VAR)
    if env_override:
        candidate = pathlib.Path(env_override)
        if not candidate.exists():
            raise FileNotFoundError(
                f"Database config not found at {candidate}. Copy config/db_config.example.ini and set {CONFIG_ENV_VAR} if needed."
            )
        return _load_from_path(candidate)

    candidates: list[pathlib.Path] = []
    if path:
        candidates.append(path)
    candidates.extend([USER_CONFIG_PATH, PACKAGE_CONFIG_PATH])

    for candidate in candidates:
        if candidate.exists():
            return _load_from_path(candidate)

    tried = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(
        f"Database config not found. Provide {CONFIG_ENV_VAR} or create one of: {tried}"
    )
