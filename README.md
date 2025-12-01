# FITS CLI

A small Python CLI scaffold for running FITS analysis workflows. It currently supports two analysis modes and can optionally upload the generated CSV artifacts to a MySQL database.

## Installation

Install the package so you can invoke it from any working directory:

```bash
pip install .
```

## Commands

### Analyze

Runs an analysis in a specified mode and writes CSV artifacts.

```bash
python -m fits.run analyze --mode dtk [--device-type <name>] [--upload | --upload-test]
python -m fits.run analyze --mode coverage [--device-type <name>] [--upload | --upload-test]
```

Options:
- `--device-type` — optional label to record the device type with the execution; the
  value is stored in the `executions` table when uploads are enabled.
- `--upload` — upload generated CSV files to MySQL after writing them. Uploads also
  create a single row in the `executions` table with the generated `exec_id`, the
  chosen mode as `type`, and the absolute path of the execution directory stored as
  `exec_dir`. Execution identifiers are generated inside the uploader as 18-digit
  integers shaped like `YYYYMMDDHHMMSS` + two random digits + a mode task id
  (`01` for `dtk`, `02` for `coverage`).
- `--upload-test` — same as `--upload` but generates an `exec_id` prefixed with `9999`
  so you can distinguish test uploads from normal runs.

Each run writes its artifacts into a single folder under the working directory named `FITS-RESULTS-<exec_id>`. Each mode currently writes a single, easy-to-read CSV defined in `fits/analyzers/*.py` so you can swap in your own logic without hunting through other files. DTK emits many rows with three columns (`exec_id`, `case`, `result`) where `result` is a 10-decimal fractional value; case names are simple "Path_Clip_*" strings to keep the structure obvious.
Output filenames follow the pattern `fits.db.<database>.<table>.csv` to match the MySQL table and database names used during upload.

### DTK case-to-module mapping

DTK results can enrich each case with module and owner metadata by reading two optional CSVs from the working directory: `casename-to-module.csv` and `module-to-owner.csv`. When resolving modules, only the case prefix (the letters before the first `_` in the case name) is compared to the `casename` column in `casename-to-module.csv`, so mappings remain stable even when additional suffixes appear in case identifiers.

## Configuration

Database connection settings are loaded from `~/.config/fits/db_config.ini` (or a path pointed to by the `FITS_DB_CONFIG` environment variable). A repository-local `config/db_config.ini` is still honored for development. Copy `config/db_config.example.ini` to your config location, fill in your host, user, password, and database, and keep real credentials out of the codebase.

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
