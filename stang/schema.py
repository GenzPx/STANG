"""Schema inference and validation for STG containers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

TYPE_STRING = "string"
TYPE_INTEGER = "integer"
TYPE_FLOAT = "float"
TYPE_BOOLEAN = "boolean"
TYPE_NULL = "null"
TYPE_ARRAY = "array"
TYPE_OBJECT = "object"
TYPE_ANY = "any"

SUPPORTED_TYPES = frozenset(
    {
        TYPE_STRING,
        TYPE_INTEGER,
        TYPE_FLOAT,
        TYPE_BOOLEAN,
        TYPE_NULL,
        TYPE_ARRAY,
        TYPE_OBJECT,
        TYPE_ANY,
    }
)

JSONCompatible = str | int | float | bool | None | list[Any] | dict[str, Any]


class SchemaError(ValueError):
    """Raised when schema inference or validation fails."""


def _merge_field_types(existing: str, incoming: str) -> str:
    """Resolve two inferred types for the same field across multiple records."""
    if existing == incoming:
        return existing
    if existing == TYPE_NULL:
        return incoming
    if incoming == TYPE_NULL:
        return existing
    if {existing, incoming} == {TYPE_INTEGER, TYPE_FLOAT}:
        return TYPE_FLOAT
    return TYPE_ANY


class Schema:
    """A lightweight schema describing the shape of records in a container.

    Nested object schemas are flattened using dot-notation for field names.
    """

    def __init__(self, fields: Mapping[str, str] | None = None) -> None:
        """Initialize a schema from a mapping of field names to STANG types."""
        self.fields: dict[str, str] = dict(fields or {})
        self._validate()

    def _validate(self) -> None:
        for name, kind in self.fields.items():
            if not isinstance(name, str) or not name:
                raise SchemaError("Schema field names must be non-empty strings.")
            if kind not in SUPPORTED_TYPES:
                raise SchemaError(f"Unsupported schema type: {kind!r}")

    @classmethod
    def infer(cls, record: Mapping[str, Any]) -> Schema:
        """Infer a flattened schema from a single record."""
        fields: dict[str, str] = {}
        for key, value in record.items():
            for sub_key, kind in cls._infer_value(key, value).items():
                fields[sub_key] = kind
        return cls(fields)

    @classmethod
    def infer_many(cls, records: Sequence[Mapping[str, Any]]) -> Schema:
        """Infer a unified flattened schema across a sequence of records."""
        merged_fields: dict[str, str] = {}
        for record in records:
            if not isinstance(record, Mapping):
                raise SchemaError(f"Expected mapping record, got {type(record).__name__}")
            record_schema = cls.infer(record)
            for name, kind in record_schema.fields.items():
                if name in merged_fields:
                    merged_fields[name] = _merge_field_types(merged_fields[name], kind)
                else:
                    merged_fields[name] = kind
        return cls(merged_fields)

    def merge(self, other: Schema) -> Schema:
        """Return a new schema combining fields from both schemas."""
        combined = dict(self.fields)
        for name, kind in other.fields.items():
            if name in combined:
                combined[name] = _merge_field_types(combined[name], kind)
            else:
                combined[name] = kind
        return Schema(combined)

    def validate_record(self, record: Mapping[str, Any], *, allow_extra: bool = True) -> None:
        """Validate a record against this schema.

        Args:
            record: Mapping to validate.
            allow_extra: Whether fields absent from the schema are permitted.

        Raises:
            SchemaError: If a field violates its declared schema type.
        """
        inferred = self.infer(record)
        for name, actual_kind in inferred.fields.items():
            if name not in self.fields:
                if not allow_extra:
                    raise SchemaError(f"Unexpected field not in schema: {name!r}")
                continue
            expected_kind = self.fields[name]
            if expected_kind == TYPE_ANY or actual_kind == TYPE_NULL:
                continue
            if expected_kind == TYPE_FLOAT and actual_kind == TYPE_INTEGER:
                continue
            if actual_kind != expected_kind:
                raise SchemaError(
                    f"Field {name!r} expected type {expected_kind!r}, got {actual_kind!r}"
                )

    @classmethod
    def _infer_value(cls, prefix: str, value: Any) -> dict[str, str]:
        kind = cls.classify(value)
        if kind == TYPE_OBJECT and isinstance(value, dict):
            if not value:
                return {prefix: TYPE_OBJECT}
            nested: dict[str, str] = {}
            for sub_key, sub_value in value.items():
                nested.update(cls._infer_value(f"{prefix}.{sub_key}", sub_value))
            return nested
        return {prefix: kind}

    @staticmethod
    def classify(value: Any) -> str:
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
        """Convert schema to a serializable dictionary."""
        return {"fields": self.fields}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Schema:
        """Reconstruct a schema from its serialized dictionary form."""
        fields = data.get("fields", {})
        if not isinstance(fields, Mapping):
            raise SchemaError("Schema 'fields' entry must be a mapping.")
        return cls(fields)

    def __eq__(self, other: object) -> bool:
        """Compare two schemas by field definitions."""
        if not isinstance(other, Schema):
            return NotImplemented
        return self.fields == other.fields

    def __repr__(self) -> str:
        """Return developer-readable string representation."""
        return f"{self.__class__.__name__}(fields={self.fields!r})"
