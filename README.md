# FITS CLI

A small Python CLI scaffold for running FITS analysis workflows. It currently supports two analysis modes and can optionally upload the generated CSV artifacts to a MySQL database.

## Commands

### Analyze

Runs an analysis in a specified mode and writes CSV artifacts.

```bash
python -m fits.run analyze --mode dtk [--upload | --upload-test]
python -m fits.run analyze --mode coverage [--upload | --upload-test]
```

Options:
- `--upload` — upload generated CSV files to MySQL after writing them. Uploads also
  create a single row in the `executions` table with the generated `exec_id`, the
  chosen mode as `type`, and the absolute path of the execution directory stored as
  `exec_dir`. Execution identifiers are generated inside the uploader as 18-digit
  integers shaped like `YYYYMMDDHHMMSS` + two random digits + a mode task id
  (`01` for `dtk`, `02` for `coverage`).
- `--upload-test` — same as `--upload` but generates an `exec_id` prefixed with `9999`
  so you can distinguish test uploads from normal runs.

Each run writes its artifacts into a single folder under the working directory named `FITS-RESULTS-<exec_id>`. Each mode currently writes a single, easy-to-read CSV defined in `fits/analyzers/*.py` so you can swap in your own logic without hunting through other files. DTK emits many rows with three columns (`exec_id`, `case`, `result`) where `result` is a 10-decimal fractional value; case names are simple "Path_Clip_*" strings to keep the structure obvious.
Output filenames follow the pattern `fitsdb-<exec_id>.<table>.csv` to match the MySQL table names used during upload.

## Configuration

Database connection settings are loaded from `config/db_config.ini` (or a path pointed to by the `FITS_DB_CONFIG` environment variable). Copy `config/db_config.example.ini` to `config/db_config.ini`, fill in your host, user, password, and database, and keep real credentials out of the codebase.

Uploads rely on the `executions` table (for the execution row) plus any tables referenced by analyzer CSVs (e.g., `dtk_summary` or `coverage_summary`).

## Development Notes

- CSV shapes are defined via `CsvArtifact` objects in `fits/artifacts.py`.
- Analyzer entry points are registered in `fits/analyzers/__init__.py`.
- Upload helpers are defined in `fits/uploader.py` and can ingest multiple CSV files.

## How artifacts work

`fits/artifacts.py` contains small helpers for describing and writing CSV outputs. Each analyzer returns a list of `CsvArtifact`
instances that name the file, list the headers, and provide row data. The shared `write_csv` utility ensures the output
directory exists, writes the headers, and persists every row so analyzers can focus solely on producing data rather than file
I/O details.
