"""Public adapter facade and recursive row expansion implementation."""

from __future__ import annotations

import typing as t
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

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


@dataclass
class _RowBudget:
    """Track rows yielded by one public adaptation call."""

    max_rows: int | None
    adapter_name: str
    emitted: int = 0

    def claim(self) -> None:
        """Claim one output row or raise when the limit is exceeded."""
        next_count = self.emitted + 1
        if self.max_rows is not None and next_count > self.max_rows:
            raise RowLimitExceeded(self.max_rows, next_count, self.adapter_name)
        self.emitted = next_count


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
    def _source_mapping(cls, line: DATA_FOR_ADAPT) -> Mapping[str, object]:
        """Normalize optional input into a mapping for field extraction."""
        if line is None:
            return {}
        if isinstance(line, Mapping):
            return line
        raise InvalidShapeError(f"`{cls.__name__}` expects a mapping input")

    @classmethod
    def _iter_source(
        cls,
        line: DATA_FOR_ADAPT,
        parent_is_optional: bool,
        budget: _RowBudget,
        claim_rows: bool,
    ) -> Iterator[FlatRow]:
        """Lazily adapt one source mapping using a shared row budget."""
        source = cls._source_mapping(line)
        fields = tuple(cls.adapter_fields())
        yield from cls._iter_fields(source, fields, 0, {}, parent_is_optional, budget, claim_rows)

    @classmethod
    def _iter_fields(
        cls,
        source: Mapping[str, object],
        fields: tuple[tuple[str, AdapterField], ...],
        index: int,
        current_row: FlatRow,
        parent_is_optional: bool,
        budget: _RowBudget,
        claim_rows: bool,
    ) -> Iterator[FlatRow]:
        """Recursively combine field rows without materializing expansions."""
        if index == len(fields):
            if claim_rows:
                budget.claim()
            yield current_row
            return

        _, field_info = fields[index]
        value = cls._read_field(source, field_info)
        for field_row in cls._iter_field_rows(value, field_info, parent_is_optional, budget):
            merged_row = cls._merge_row(current_row, field_row)
            yield from cls._iter_fields(
                source,
                fields,
                index + 1,
                merged_row,
                parent_is_optional,
                budget,
                claim_rows,
            )

    @classmethod
    def _iter_field_rows(
        cls,
        value: object,
        field_info: AdapterField,
        parent_is_optional: bool,
        budget: _RowBudget,
    ) -> Iterator[FlatRow]:
        """Yield rows produced by one scalar or nested adapter field."""
        if field_info.adapter_type is not None:
            yield from cls._iter_nested(value, field_info, parent_is_optional, budget)
            return

        field_name = f"{cls.__name__}.{field_info.field_name}"
        converted = convert_scalar(
            value,
            field_info.annotation,
            field_name,
            field_info.optional,
            parent_is_optional,
        )
        yield {field_info.output_name: converted}

    @classmethod
    def _iter_nested(
        cls,
        value: object,
        field_info: AdapterField,
        parent_is_optional: bool,
        budget: _RowBudget,
    ) -> Iterator[FlatRow]:
        """Lazily yield rows for one nested mapping or list field."""
        adapter_type = field_info.adapter_type
        if adapter_type is None:
            raise InvalidShapeError(f"Field `{field_info.field_name}` has no nested adapter")

        if field_info.is_list:
            if value is MISSING:
                if not field_info.optional:
                    raise MissingFieldError(field_info.field_name, cls.__name__)
                value = None

            if value is None or value == []:
                yield from cls._iter_child(adapter_type, None, True, field_info.field_name, budget)
                return
            if not isinstance(value, list):
                raise InvalidShapeError(f"Field `{field_info.field_name}` must contain a list")

            for item in value:
                if not isinstance(item, Mapping):
                    raise InvalidShapeError(f"Items of `{field_info.field_name}` must be mappings")
                yield from cls._iter_child(adapter_type, item, False, field_info.field_name, budget)
            return

        if value is MISSING:
            if field_info.optional:
                value = None
            else:
                raise MissingFieldError(field_info.field_name, cls.__name__)
        if value is None:
            yield from cls._iter_child(
                adapter_type,
                None,
                field_info.optional or parent_is_optional,
                field_info.field_name,
                budget,
            )
            return
        if not isinstance(value, Mapping):
            raise InvalidShapeError(f"Field `{field_info.field_name}` must contain a mapping")
        yield from cls._iter_child(adapter_type, value, parent_is_optional, field_info.field_name, budget)

    @classmethod
    def _iter_child(
        cls,
        adapter_type: type[AdapterBase],
        value: DATA_FOR_ADAPT,
        parent_is_optional: bool,
        field_name: str,
        budget: _RowBudget,
    ) -> Iterator[FlatRow]:
        """Lazily adapt a child and add its parent field path to errors."""
        child_type = t.cast(type[FlatAdapter], adapter_type)
        try:
            yield from child_type._iter_source(value, parent_is_optional, budget, False)
        except MissingFieldError as exc:
            child_field_name = exc.field_name.rsplit(".", maxsplit=1)[-1]
            raise MissingFieldError(f"{field_name}.{child_field_name}", cls.__name__) from exc

    @classmethod
    def _merge_row(cls, left: FlatRow, right: FlatRow) -> FlatRow:
        """Merge two rows while rejecting duplicate output columns."""
        overlap = set(left).intersection(right)
        if overlap:
            raise DuplicateFieldError(overlap, cls.__name__)
        merged: FlatRow = dict(left)
        merged.update(right)
        return merged

    @classmethod
    def iter_adapt(
        cls,
        line: DATA_FOR_ADAPT,
        parent_is_optional: bool = False,
        *,
        max_rows: int | None = None,
    ) -> Iterator[FlatRow]:
        """Lazily adapt one mapping into flat rows.

        Args:
            line: Mapping to flatten. ``None`` is used for optional parents.
            parent_is_optional: Whether missing child scalar values are allowed.
            max_rows: Optional positive limit for the complete expansion.

        Returns:
            An iterator that yields rows in declaration and input order.

        Raises:
            InvalidShapeError: If the root input has an invalid shape.
            InvalidRowLimitError: If ``max_rows`` is not positive.
            MissingFieldError: When iteration reaches a missing required field.
            ConversionError: When iteration reaches an invalid scalar value.
            DuplicateFieldError: When iteration reaches duplicate output keys.
            RowLimitExceeded: When iteration would yield more than ``max_rows``.

        """
        cls._validate_max_rows(max_rows)
        cls._source_mapping(line)
        budget = _RowBudget(max_rows, cls.__name__)
        return cls._iter_source(line, parent_is_optional, budget, True)

    @classmethod
    def adapt(
        cls,
        line: DATA_FOR_ADAPT,
        parent_is_optional: bool = False,
        *,
        max_rows: int | None = None,
    ) -> FlatRows:
        """Eagerly adapt one mapping by consuming :meth:`iter_adapt`.

        Args:
            line: Mapping to flatten. ``None`` is used for optional parents.
            parent_is_optional: Whether missing child scalar values are allowed.
            max_rows: Optional positive limit for the complete expansion.

        Returns:
            All generated rows in declaration and input order.

        """
        return list(
            cls.iter_adapt(
                line,
                parent_is_optional=parent_is_optional,
                max_rows=max_rows,
            )
        )
