"""CSV dumper plugin."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from typing import Any

from stang.container import STGContainer
from stang.decoder import decode_stg
from stang.dumpers.base import Dumper


def collect_fieldnames(records: Sequence[dict[str, Any]]) -> list[str]:
    """Return the sorted union of keys across *records*."""
    keys: set[str] = set()
    for record in records:
        keys.update(record.keys())
    return sorted(keys)


class CSVDumper(Dumper):
    """Dump container records as CSV.

    Nested objects are serialized as JSON within the CSV cell.
    """

    name = "csv"

    delimiter = ","

    def dump(self, container: STGContainer) -> str:
        """Render records as delimited text (comma by default)."""
        records = decode_stg(container)
        if not records:
            return ""
        fieldnames = collect_fieldnames(records)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=self.delimiter)
        writer.writeheader()
        for record in records:
            writer.writerow(flatten_record(record, fieldnames))
        return output.getvalue()


def flatten_record(record: dict[str, Any], fieldnames: Sequence[str]) -> dict[str, str]:
    """Flatten one record into strings suitable for delimited output."""
    result: dict[str, str] = {}
    for key in fieldnames:
        value = record.get(key, "")
        if isinstance(value, (dict, list, tuple)):
            result[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        elif value is None:
            result[key] = ""
        else:
            result[key] = str(value)
    return result
