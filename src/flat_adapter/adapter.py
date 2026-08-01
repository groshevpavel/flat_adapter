"""Public adapter facade and recursive row expansion implementation."""

from __future__ import annotations

from collections.abc import Mapping

from .base import (
    DATA_FOR_ADAPT,
    MISSING,
    AdapterBase,
    AdapterField,
    Field,
    FlatRow,
    FlatRows,
    convert_scalar,
)
from .errors import (
    DuplicateFieldError,
    InvalidRowLimitError,
    InvalidShapeError,
    MissingFieldError,
    RowLimitExceeded,
)

field = Field


class FlatAdapter(AdapterBase):
    """Convert nested mappings into deterministic flat rows.

    Subclasses declare output fields with annotations. Nested adapter fields
    are recursively expanded, and list-valued fields are combined as a
    deterministic Cartesian product.
    """

    @classmethod
    def _read_field(cls, line: Mapping[str, object], field: AdapterField) -> object:
        """Read one field from the source mapping or configured transformer."""
        if field.field is not None:
            try:
                return field.field.resolve(line, field.field_name, field.optional)
            except MissingFieldError as exc:
                raise MissingFieldError(field.field_name, cls.__name__) from exc

        if field.transformer is not None:
            return field.transformer(line)

        return line.get(field.field_name, MISSING)

    @classmethod
    def _validate_max_rows(cls, max_rows: int | None) -> None:
        """Validate the optional row expansion limit."""
        if max_rows is not None and max_rows <= 0:
            raise InvalidRowLimitError(max_rows)

    @classmethod
    def _ensure_row_limit(cls, row_count: int, max_rows: int | None) -> None:
        """Raise before materializing more rows than the configured limit."""
        if max_rows is not None and row_count > max_rows:
            raise RowLimitExceeded(max_rows, row_count, cls.__name__)

    @classmethod
    def _adapt_nested(
        cls,
        value: object,
        field: AdapterField,
        parent_is_optional: bool,
        max_rows: int | None,
    ) -> FlatRows:
        """Adapt one nested mapping or list-valued nested field."""
        adapter_type = field.adapter_type
        if adapter_type is None:
            raise InvalidShapeError(f"Field `{field.field_name}` has no nested adapter")

        if field.is_list:
            if value is MISSING:
                if not field.optional:
                    raise MissingFieldError(field.field_name, cls.__name__)
                value = None

            if value is None or value == []:
                return cls._adapt_child(adapter_type, None, True, field.field_name, max_rows)
            if not isinstance(value, list):
                raise InvalidShapeError(f"Field `{field.field_name}` must contain a list")

            rows: FlatRows = []
            for item in value:
                if not isinstance(item, Mapping):
                    raise InvalidShapeError(f"Items of `{field.field_name}` must be mappings")
                child_rows = cls._adapt_child(adapter_type, item, False, field.field_name, max_rows)
                cls._ensure_row_limit(len(rows) + len(child_rows), max_rows)
                rows.extend(child_rows)
            return rows

        if value is MISSING:
            if field.optional:
                value = None
            else:
                raise MissingFieldError(field.field_name, cls.__name__)
        if value is None:
            return cls._adapt_child(
                adapter_type,
                None,
                field.optional or parent_is_optional,
                field.field_name,
                max_rows,
            )
        if not isinstance(value, Mapping):
            raise InvalidShapeError(f"Field `{field.field_name}` must contain a mapping")
        return cls._adapt_child(adapter_type, value, parent_is_optional, field.field_name, max_rows)

    @classmethod
    def _adapt_child(
        cls,
        adapter_type: type[AdapterBase],
        value: DATA_FOR_ADAPT,
        parent_is_optional: bool,
        field_name: str,
        max_rows: int | None,
    ) -> FlatRows:
        """Adapt a child and add the parent field path to missing-field errors."""
        try:
            return adapter_type.adapt(
                value,
                parent_is_optional=parent_is_optional,
                max_rows=max_rows,
            )
        except MissingFieldError as exc:
            child_field_name = exc.field_name.rsplit(".", maxsplit=1)[-1]
            raise MissingFieldError(f"{field_name}.{child_field_name}", cls.__name__) from exc

    @classmethod
    def _merge_rows(
        cls,
        left: FlatRows,
        right: FlatRows,
        max_rows: int | None,
    ) -> FlatRows:
        """Merge two row sets while rejecting duplicate output columns."""
        cls._ensure_row_limit(len(left) * len(right), max_rows)
        result: FlatRows = []
        for left_row in left:
            for right_row in right:
                overlap = set(left_row).intersection(right_row)
                if overlap:
                    raise DuplicateFieldError(overlap, cls.__name__)
                merged: FlatRow = dict(left_row)
                merged.update(right_row)
                result.append(merged)
        return result

    @classmethod
    def adapt(
        cls,
        line: DATA_FOR_ADAPT,
        parent_is_optional: bool = False,
        *,
        max_rows: int | None = None,
    ) -> FlatRows:
        """Adapt one mapping into one or more flat rows.

        Args:
            line: Mapping to flatten. ``None`` is used for optional parents.
            parent_is_optional: Whether missing child scalar values are allowed.
            max_rows: Optional positive limit for the complete expansion.

        Returns:
            Rows in declaration order, with nested lists expanded.

        Raises:
            InvalidShapeError: If the input or a nested value has an invalid shape.
            MissingFieldError: If a required field is absent.
            ConversionError: If a scalar cannot be converted.
            DuplicateFieldError: If nested adapters produce the same key.
            InvalidRowLimitError: If ``max_rows`` is not positive.
            RowLimitExceeded: If expansion would exceed ``max_rows``.

        """
        cls._validate_max_rows(max_rows)
        if line is None:
            source: Mapping[str, object] = {}
        elif isinstance(line, Mapping):
            source = line
        else:
            raise InvalidShapeError(f"`{cls.__name__}` expects a mapping input")

        rows: FlatRows = [{}]
        for _, field in cls.adapter_fields():
            value = cls._read_field(source, field)
            if field.adapter_type is not None:
                nested_rows = cls._adapt_nested(value, field, parent_is_optional, max_rows)
            else:
                field_name = f"{cls.__name__}.{field.field_name}"
                converted = convert_scalar(
                    value,
                    field.annotation,
                    field_name,
                    field.optional,
                    parent_is_optional,
                )
                nested_rows = [{field.output_name: converted}]
            rows = cls._merge_rows(rows, nested_rows, max_rows)
        return rows
