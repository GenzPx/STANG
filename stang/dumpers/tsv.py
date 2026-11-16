"""TSV dumper plugin."""

from __future__ import annotations

from stang.dumpers.csv import CSVDumper


class TSVDumper(CSVDumper):
    """Dump container records as tab-separated values."""

    name = "tsv"

    delimiter = "\t"
