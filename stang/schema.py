"""Schema inference and validation for STG containers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, get_args

# Minimal type system used by STANG.
TYPE_STRING = "string"
TYPE_INTEGER = "integer"
TYPE_FLOAT = "float"
TYPE_BOOLEAN = "boolean"
TYPE_NULL = "null"
TYPE_ARRAY = "array"
TYPE_OBJECT = "object"

SUPPORTED_TYPES = frozenset(
    {TYPE_STRING, TYPE_INTEGER, TYPE_FLOAT, TYPE_BOOLEAN, TYPE_NULL, TYPE_ARRAY, TYPE_OBJECT}
)

JSONCompatible = str | int | float | bool | None | list[Any] | dict[str, Any]


class SchemaError(ValueError):
    """Raised when schema inference or validation fails."""


class Schema:
    """A lightweight schema describing the shape of records in a container.

    The schema is intentionally permissive: for the MVP it stores a list of
    field names and their inferred primitive types. Nested object schemas are
    flattened using dot-notation for field names.
    """

    def __init__(self, fields: Mapping[str, str] | None = None) -> None:
        self.fields: dict[str, str] = dict(fields or {})
        self._validate()

    def _validate(self) -> None:
        for name, kind in self.fields.items():
            if not isinstance(name, str) or not name:
                raise SchemaError("Schema field names must be non-empty strings.")
            if kind not in SUPPORTED_TYPES:
                raise SchemaError(f"Unsupported schema type: {kind!r}")

    @classmethod
    def infer(cls, record: Mapping[str, JSONCompatible]) -> "Schema":
        """Infer a flattened schema from a single record."""
        fields: dict[str, str] = {}
        for key, value in record.items():
            for sub_key, kind in cls._infer_value(key, value).items():
                fields[sub_key] = kind
        return cls(fields)

    @classmethod
    def _infer_value(cls, prefix: str, value: JSONCompatible) -> dict[str, str]:
        kind = cls.classify(value)
        if kind == TYPE_OBJECT and isinstance(value, dict):
            nested: dict[str, str] = {}
            for sub_key, sub_value in value.items():
                nested.update(cls._infer_value(f"{prefix}.{sub_key}", sub_value))
            return nested
        return {prefix: kind}

    @staticmethod
    def classify(value: JSONCompatible) -> str:
        """Classify a JSON-compatible value into a STANG type name."""
        if value is None:
            return TYPE_NULL
        if isinstance(value, bool):
            return TYPE_BOOLEAN
        if isinstance(value, int):
            return TYPE_INTEGER
        if isinstance(value, float):
            return TYPE_FLOAT
        if isinstance(value, str):
            return TYPE_STRING
        if isinstance(value, (list, tuple)):
            return TYPE_ARRAY
        if isinstance(value, dict):
            return TYPE_OBJECT
        raise SchemaError(f"Unsupported Python type: {type(value).__name__}")

    def to_dict(self) -> dict[str, Any]:
        return {"fields": self.fields}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Schema":
        return cls(data.get("fields", {}))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Schema):
            return NotImplemented
        return self.fields == other.fields

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(fields={self.fields!r})"
