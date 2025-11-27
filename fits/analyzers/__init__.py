"""Analyzer entry points for the FITS CLI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from ..artifacts import CsvArtifact
from ..config import RunContext
from .coverage import build_coverage_artifacts
from .dtk import build_dtk_artifacts


Analyzer = Callable[[RunContext], Iterable[CsvArtifact]]


@dataclass
class AnalyzerSpec:
    name: str
    build: Analyzer


def available_analyzers() -> dict[str, AnalyzerSpec]:
    return {
        "dtk": AnalyzerSpec(name="dtk", build=build_dtk_artifacts),
        "coverage": AnalyzerSpec(name="coverage", build=build_coverage_artifacts),
    }
