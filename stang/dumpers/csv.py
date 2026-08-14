"""CSV dumper plugin."""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence

from stang.container import STGContainer
from stang.decoder import decode_stg
from stang.dumpers import Dumper


class CSVDumper(Dumper):
    """Dump container records as CSV.

    Nested objects are serialized as JSON within the CSV cell.
    """

    name = "csv"

    def dump(self, container: STGContainer) -> str:
        records = decode_stg(container)
        if not records:
            return ""

        fieldnames = self._collect_fieldnames(records)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(self._flatten(record, fieldnames))
        return output.getvalue()

    @staticmethod
    def _collect_fieldnames(records: Sequence[dict]) -> list[str]:
        keys: set[str] = set()
        for record in records:
            keys.update(record.keys())
        return sorted(keys)

    @staticmethod
    def _flatten(record: dict, fieldnames: list[str]) -> dict[str, str]:
        import json

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
