"""Public package exports for flat-adapter."""

from .adapter import FlatAdapter, field
from .base import ADOPTED_DATA, ADOPTED_DATA_AS_LIST, DATA_FOR_ADAPT, AdapterBase, AdapterField, Field
from .errors import (
    ConversionError,
    DuplicateFieldError,
    FlatAdapterError,
    InvalidRowLimitError,
    InvalidShapeError,
    MissingFieldError,
    RowLimitError,
    RowLimitExceeded,
    TypeResolutionError,
)

__all__ = [
    "ADOPTED_DATA",
    "ADOPTED_DATA_AS_LIST",
    "DATA_FOR_ADAPT",
    "AdapterBase",
    "AdapterField",
    "ConversionError",
    "DuplicateFieldError",
    "Field",
    "FlatAdapterError",
    "FlatAdapter",
    "InvalidRowLimitError",
    "InvalidShapeError",
    "MissingFieldError",
    "RowLimitExceeded",
    "RowLimitError",
    "TypeResolutionError",
    "field",
]
