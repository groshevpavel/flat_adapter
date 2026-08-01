"""Exception types raised by the flat-adapter transformation core."""

from __future__ import annotations


class FlatAdapterError(ValueError):
    """Base class for all adapter errors."""


class MissingFieldError(FlatAdapterError):
    """Raised when a required field is absent."""

    def __init__(self, field_name: str, adapter_name: str) -> None:
        """Create an error describing the missing field and adapter."""
        self.field_name = field_name
        self.adapter_name = adapter_name
        super().__init__(f"Required field `{field_name}` is missing for `{adapter_name}`")


class ConversionError(FlatAdapterError):
    """Raised when a scalar value cannot be converted."""

    def __init__(self, field_name: str, target_type: object, value: object) -> None:
        """Create an error with the field, target type, and original value."""
        self.field_name = field_name
        self.target_type = target_type
        self.value = value
        super().__init__(f"Cannot convert field `{field_name}` to `{target_type}`: {value!r}")


class InvalidShapeError(FlatAdapterError):
    """Raised when an input value has an unsupported nested shape."""


class RowLimitError(FlatAdapterError):
    """Base class for row-expansion limit errors."""


class InvalidRowLimitError(RowLimitError):
    """Raised when a row limit is not a positive integer."""

    def __init__(self, max_rows: int) -> None:
        """Create an error for an invalid row limit."""
        self.max_rows = max_rows
        super().__init__(f"Row limit must be positive, got {max_rows!r}")


class RowLimitExceeded(RowLimitError):
    """Raised before expansion would exceed the configured row limit."""

    def __init__(self, max_rows: int, attempted_rows: int, adapter_name: str) -> None:
        """Create an error describing the attempted and allowed row counts."""
        self.max_rows = max_rows
        self.attempted_rows = attempted_rows
        self.adapter_name = adapter_name
        super().__init__(
            f"Row expansion in `{adapter_name}` attempted {attempted_rows} rows; maximum of {max_rows} is allowed"
        )


class DuplicateFieldError(FlatAdapterError):
    """Raised when two nested adapters produce the same output key."""

    def __init__(self, keys: set[str], adapter_name: str) -> None:
        """Create an error describing duplicate keys and their adapter."""
        self.keys = frozenset(keys)
        self.adapter_name = adapter_name
        super().__init__(f"Duplicate output keys {sorted(keys)!r} in `{adapter_name}`")


class TypeResolutionError(FlatAdapterError):
    """Raised when an annotation cannot be resolved."""
