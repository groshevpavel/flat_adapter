"""Unit tests for field extraction and scalar conversion."""

import datetime
from typing import Annotated, cast

import pytest

from flat_adapter import ConversionError, Field, FlatAdapter, MissingFieldError, TypeResolutionError


class ScalarAdapter(FlatAdapter):
    """Declare fields that exercise scalar conversion."""

    integer: int
    amount: float
    enabled: bool
    created_at: datetime.datetime
    note: str | None


class FieldAdapter(FlatAdapter):
    """Declare fields with paths, defaults, and preprocessors."""

    value: Annotated[int, Field(source="payload.value")]
    fallback: Annotated[str, Field(source="payload.missing", default="fallback")]
    normalized: Annotated[
        str,
        Field(
            source="raw",
            prepare_data_func=lambda value: str(value).strip().lower(),
        ),
    ]


class AnnotatedFieldAdapter(FlatAdapter):
    """Declare Field metadata with the Annotated syntax."""

    value: Annotated[int, Field(source="payload.value")]


class OptionalFieldAdapter(FlatAdapter):
    """Declare an optional field with Annotated metadata."""

    value: Annotated[int | None, Field(source="missing")]


class CallableDefaultAdapter(FlatAdapter):
    """Declare a field whose default is produced by a factory."""

    value: Annotated[str, Field(source="missing", default=lambda: "generated")]


class TransformAdapter(FlatAdapter):
    """Declare a field with a scalar preprocessing function."""

    normalized: Annotated[
        str,
        Field(
            source="raw",
            prepare_data_func=lambda value: str(value).strip().lower(),
        ),
    ]


class RawValueAdapter(FlatAdapter):
    """Declare an untyped object field."""

    value: object


class DateAdapter(FlatAdapter):
    """Declare a date field."""

    day: datetime.date


BrokenReferenceAdapter = cast(
    type[FlatAdapter],
    type(
        "BrokenReferenceAdapter",
        (FlatAdapter,),
        {
            "__annotations__": {"child": "MissingChild"},
            "__doc__": "Declare an adapter with an unresolved reference.",
        },
    ),
)


def test_scalar_values_are_converted_and_optional_values_are_preserved() -> None:
    """Convert supported scalar types and preserve explicit None values."""
    result = ScalarAdapter.adapt(
        {
            "integer": "7",
            "amount": "12,50",
            "enabled": "yes",
            "created_at": "2026-08-01 12:00:00",
            "note": None,
        }
    )

    assert result == [
        {
            "integer": 7,
            "amount": 12.5,
            "enabled": True,
            "created_at": datetime.datetime(2026, 8, 1, 12, 0),
            "note": None,
        }
    ]


def test_missing_required_scalar_raises_typed_error() -> None:
    """Reject a missing required scalar with a typed exception."""
    with pytest.raises(MissingFieldError, match="ScalarAdapter"):
        ScalarAdapter.adapt({})


def test_invalid_scalar_raises_conversion_error() -> None:
    """Reject a scalar that cannot be converted to its annotation."""
    with pytest.raises(ConversionError, match="integer"):
        ScalarAdapter.adapt({"integer": "not-an-int"})


def test_field_supports_nested_path_default_and_preprocessing() -> None:
    """Extract a nested source, apply a default, and preprocess a value."""
    assert FieldAdapter.adapt({"payload": {"value": "9"}, "raw": "  VALUE "}) == [
        {"value": 9, "fallback": "fallback", "normalized": "value"}
    ]


def test_annotated_field_configuration_does_not_need_a_cast() -> None:
    """Support Field metadata without a class-body cast."""
    assert AnnotatedFieldAdapter.adapt({"payload": {"value": "9"}}) == [{"value": 9}]


def test_field_reports_missing_required_path() -> None:
    """Report a missing required Field source path."""
    with pytest.raises(MissingFieldError, match="value"):
        FieldAdapter.adapt({"payload": {}})


def test_field_supports_optional_and_callable_defaults() -> None:
    """Support optional metadata and callable defaults."""
    assert OptionalFieldAdapter.adapt({}) == [{"value": None}]
    assert CallableDefaultAdapter.adapt({}) == [{"value": "generated"}]


def test_callable_field_transformer_receives_the_whole_mapping() -> None:
    """Apply a configured field preprocessor before scalar conversion."""
    assert TransformAdapter.adapt({"raw": "  VALUE "}) == [{"normalized": "value"}]


def test_object_values_are_returned_without_conversion() -> None:
    """Return values annotated as object without coercion."""
    payload = {"key": "value"}

    assert RawValueAdapter.adapt({"value": payload}) == [{"value": payload}]


def test_date_values_are_converted() -> None:
    """Convert an ISO date string to a date instance."""
    assert DateAdapter.adapt({"day": "2026-08-01"}) == [{"day": datetime.date(2026, 8, 1)}]


def test_schema_exposes_compiled_output_fields() -> None:
    """Expose compiled output names and annotations through schema."""
    assert ScalarAdapter.schema()["integer"] is int


def test_unresolvable_forward_reference_raises_typed_error() -> None:
    """Reject an annotation that cannot be resolved."""
    with pytest.raises(TypeResolutionError, match="BrokenReferenceAdapter"):
        BrokenReferenceAdapter.adapt({"child": {}})
