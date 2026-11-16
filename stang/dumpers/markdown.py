"""Markdown dumper plugin."""

from __future__ import annotations

from typing import Any

from stang.container import STGContainer
from stang.decoder import decode_stg
from stang.dumpers.base import Dumper
from stang.dumpers.csv import collect_fieldnames


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif isinstance(value, (dict, list, tuple)):
        import json

        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


class MarkdownDumper(Dumper):
    """Dump container records as a GitHub-flavoured Markdown table."""

    name = "markdown"

    def dump(self, container: STGContainer) -> str:
        """Render records as a Markdown table."""
        records = decode_stg(container)
        if not records:
            return "_Empty container — no records._"
        fieldnames = collect_fieldnames(records)
        lines = [
            "| " + " | ".join(fieldnames) + " |",
            "| " + " | ".join(["---"] * len(fieldnames)) + " |",
        ]
        for record in records:
            lines.append("| " + " | ".join(_cell(record.get(k)) for k in fieldnames) + " |")
        return "\n".join(lines)
