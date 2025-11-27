"""CLI entry point for FITS workflows."""
from __future__ import annotations

import argparse
import pathlib
from typing import Sequence

from .analyzers import available_analyzers
from .artifacts import CsvArtifact, write_csv
from .config import RunContext, detect_device, load_db_config
from .uploader import UploadError, generate_exe_id, upload_coverage, upload_dtk

DEFAULT_OUTPUT_DIR = pathlib.Path("output")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="fits.run", description="FITS analysis CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Run an analysis mode")
    analyze.add_argument("--mode", choices=available_analyzers().keys(), required=True)
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
        help="Test upload with an exe_id prefixed by 9999",
    )

    return parser.parse_args(argv)


def build_context(args: argparse.Namespace) -> RunContext:
    return RunContext(
        exe_id=generate_exe_id(args.mode, test=args.upload_test),
        device=detect_device(),
        mode=args.mode,
    )


def _write_artifacts(artifacts: Sequence[CsvArtifact], output_dir: pathlib.Path):
    written: list[tuple[pathlib.Path, str]] = []
    for artifact in artifacts:
        path = write_csv(artifact, output_dir)
        if artifact.table:
            written.append((path, artifact.table))
    return written


def handle_analyze(args: argparse.Namespace) -> int:
    analyzers = available_analyzers()
    spec = analyzers[args.mode]
    context = build_context(args)

    artifacts = list(spec.build(context))
    output_dir = DEFAULT_OUTPUT_DIR / args.mode
    uploads = _write_artifacts(artifacts, output_dir)

    print(
        f"Run {context.exe_id} ({context.mode}) wrote {len(artifacts)} CSV file(s) to {output_dir}"
    )

    if args.upload or args.upload_test:
        try:
            db_config = load_db_config()
            if context.mode == "dtk":
                inserted = upload_dtk(uploads, db_config, context.exe_id)
            else:
                inserted = upload_coverage(uploads, db_config, context.exe_id)
        except (UploadError, FileNotFoundError, ValueError) as exc:
            print(f"Upload failed: {exc}")
            return 1
        print(f"Uploaded {inserted} row(s) to MySQL")

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.command == "analyze":
        return handle_analyze(args)

    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
