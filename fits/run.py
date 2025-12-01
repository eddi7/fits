"""CLI entry point for FITS workflows."""
from __future__ import annotations

import argparse
import pathlib
import subprocess
from datetime import datetime
from typing import Sequence

from .analyzers import available_analyzers
from .artifacts import CsvArtifact, build_artifact_name, write_csv
from .config import RunContext, detect_device, load_db_config
from .uploader import UploadError, generate_exec_id, upload_coverage, upload_dtk


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="fits.run", description="FITS analysis CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Run an analysis mode")
    analyze.add_argument(
        "--build-type",
        dest="build_type",
        type=str.lower,
        choices=available_analyzers().keys(),
        required=True,
    )
    analyze.add_argument(
        "--archive-dir",
        dest="archive_dir",
        type=pathlib.Path,
        help="Optional archive directory to use instead of the default",
    )
    analyze.add_argument(
        "--device-type",
        dest="device_type",
        type=str.lower,
        help="Optional device type to record with the execution",
    )
    analyze.add_argument(
        "--started-at",
        dest="started_at",
        type=datetime.fromisoformat,
        help="Optional start time for the execution (ISO 8601)",
    )
    analyze.add_argument(
        "--completed-at",
        dest="completed_at",
        type=datetime.fromisoformat,
        help="Optional completion time for the execution (ISO 8601)",
    )
    upload_group = analyze.add_mutually_exclusive_group()
    upload_group.add_argument(
        "--upload",
        action="store_true",
        help="Upload generated CSV artifacts to the configured MySQL database",
    )
    upload_group.add_argument(
        "--upload-test",
        dest="upload_test",
        action="store_true",
        help="Test upload with an exec_id prefixed by 9999",
    )

    return parser.parse_args(argv)


def build_context(args: argparse.Namespace) -> RunContext:
    db_config = load_db_config()
    exec_id = generate_exec_id(args.build_type, test=args.upload_test)
    archive_dir = args.archive_dir or pathlib.Path(f"FITS-RESULTS-{exec_id}")
    return RunContext(
        exec_id=exec_id,
        device=detect_device(),
        build_type=args.build_type,
        device_type=args.device_type,
        archive_dir=archive_dir.resolve(),
        started_at=args.started_at,
        completed_at=args.completed_at,
        db_config=db_config,
    )


def _clone_configs() -> bool:
    try:
        subprocess.run(["git-clone-configs"], check=True)
    except FileNotFoundError:
        print("Run setup failed: git-clone-configs command not found")
        return False
    except subprocess.CalledProcessError as exc:
        print(
            "Run setup failed: git-clone-configs exited with status "
            f"{exc.returncode}"
        )
        return False

    return True


def _write_artifacts(artifacts: Sequence[CsvArtifact], output_dir: pathlib.Path):
    written: list[tuple[pathlib.Path, str]] = []
    for artifact in artifacts:
        path = write_csv(artifact, output_dir)
        if artifact.table:
            written.append((path, artifact.table))
    return written


def _build_execution_artifact(context: RunContext) -> CsvArtifact:
    return CsvArtifact(
        name=build_artifact_name(context.db_config.database, "executions"),
        headers=[
            "exec_id",
            "build_type",
            "archive_dir",
            "device_type",
            "started_at",
            "completed_at",
        ],
        rows=[
            {
                "exec_id": context.exec_id,
                "build_type": context.build_type,
                "archive_dir": str(context.archive_dir),
                "device_type": context.device_type,
                "started_at": context.started_at.isoformat()
                if context.started_at
                else None,
                "completed_at": context.completed_at.isoformat()
                if context.completed_at
                else None,
            }
        ],
    )


def handle_analyze(args: argparse.Namespace) -> int:
    analyzers = available_analyzers()
    spec = analyzers[args.build_type]

    try:
        context = build_context(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Run setup failed: {exc}")
        return 1

    artifacts = [
        _build_execution_artifact(context),
        *list(spec.build(context)),
    ]
    uploads = _write_artifacts(artifacts, context.archive_dir)

    print(
        f"Run {context.exec_id} ({context.build_type}) wrote {len(artifacts)} CSV file(s) to {context.archive_dir}"
    )

    if not context.device_type:
        print("Warning: --device-type not provided; continuing without device type.")

    if args.upload or args.upload_test:
        try:
            if context.build_type == "dtk":
                inserted = upload_dtk(
                    uploads,
                    context.db_config,
                    context.exec_id,
                    context.archive_dir,
                    device_type=context.device_type,
                    started_at=context.started_at,
                    completed_at=context.completed_at,
                )
            else:
                inserted = upload_coverage(
                    uploads,
                    context.db_config,
                    context.exec_id,
                    context.archive_dir,
                    device_type=context.device_type,
                    started_at=context.started_at,
                    completed_at=context.completed_at,
                )
        except (UploadError, FileNotFoundError, ValueError) as exc:
            print(f"Upload failed: {exc}")
            return 1
        print(f"Uploaded {inserted} row(s) to MySQL")

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if not _clone_configs():
        return 1

    if args.command == "analyze":
        return handle_analyze(args)

    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
