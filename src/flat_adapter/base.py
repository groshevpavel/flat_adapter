"""Schema compilation, field metadata, and scalar conversion primitives."""

from __future__ import annotations

import datetime
import sys
import types
import typing as t
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass

from dateutil.parser import parse

from .errors import ConversionError, MissingFieldError, TypeResolutionError

InputMapping = Mapping[str, object]
DATA_FOR_ADAPT = InputMapping | None
FlatRow = dict[str, object]
FlatRows = list[FlatRow]
ADOPTED_DATA = FlatRow
ADOPTED_DATA_AS_LIST = FlatRows
MISSING = object()


def _unwrap_optional(annotation: t.Any) -> tuple[t.Any, bool]:
    """Return an annotation without its single optional wrapper."""
    origin = t.get_origin(annotation)
    if origin not in (t.Union, types.UnionType):
        return annotation, False

    args = tuple(argument for argument in t.get_args(annotation) if argument is not type(None))
    if len(args) == 1 and len(args) != len(t.get_args(annotation)):
        return args[0], True
    return annotation, False


def _adapter_type(annotation: t.Any) -> type[AdapterBase] | None:
    """Return a nested adapter class represented by an annotation."""
    if isinstance(annotation, type) and issubclass(annotation, AdapterBase):
        return annotation
    return None


class Field:
    """Describe custom extraction for one adapter field.

    Args:
        source: Input key or delimiter-separated path.
        delimiter: Path separator. The default is a dot.
        default: Value or zero-argument callable used when the source is absent.
        prepare_data_func: Optional scalar preprocessing function.

    """

    def __init__(
        self,
        source: str | None = None,
        delimiter: str = ".",
        default: object = MISSING,
        prepare_data_func: Callable[[object], object] | None = None,
    ) -> None:
        """Initialize field extraction metadata."""
        self.source = source
        self.source_delimiter = delimiter
        self.default = default
        self.prepare_data_func = prepare_data_func

    def _default_value(self, field_name: str, optional: bool) -> object:
        """Return a configured default or raise for a missing required field."""
        if self.default is not MISSING:
            if callable(self.default):
                default_factory = t.cast(Callable[[], object], self.default)
                return default_factory()
            return self.default
        if optional:
            return None
        raise MissingFieldError(field_name, "Field")

    def resolve(self, line: InputMapping, field_name: str, optional: bool) -> object:
        """Extract and optionally preprocess a value from an input mapping."""
        source = self.source or field_name
        current: object = line

        if self.source_delimiter and self.source_delimiter in source:
            for part in source.split(self.source_delimiter):
                if not isinstance(current, Mapping) or part not in current:
                    return self._default_value(field_name, optional)
                current = current[part]
        elif source not in line:
            return self._default_value(field_name, optional)
        else:
            current = line[source]

        if self.prepare_data_func is not None:
            current = self.prepare_data_func(current)
        return current

    def __call__(self, line: InputMapping | None, field_name: str, field: AdapterField) -> object:
        """Resolve a value using compiled field metadata."""
        if line is None:
            return None
        return self.resolve(line, field_name, field.optional)


def _unwrap_annotated(annotation: t.Any) -> tuple[t.Any, Field | None]:
    """Return the base annotation and the first Field metadata item."""
    if t.get_origin(annotation) is not t.Annotated:
        return annotation, None

    args = t.get_args(annotation)
    base_annotation = args[0]
    field = next((metadata for metadata in args[1:] if isinstance(metadata, Field)), None)
    return base_annotation, field


@dataclass(frozen=True, slots=True)
class AdapterField:
    """Compiled metadata for one adapter field."""

    field_name: str
    output_name: str
    annotation: t.Any
    optional: bool
    is_list: bool
    adapter_type: type[AdapterBase] | None
    field: Field | None = None
    transformer: Callable[[object], object] | None = None

    @property
    def name(self) -> str:
        """Return the output column name."""
        return self.output_name

    @property
    def is_optional(self) -> bool:
        """Return whether the field may be absent."""
        return self.optional

    @property
    def adapter(self) -> type[AdapterBase] | None:
        """Return the nested adapter type, if any."""
        return self.adapter_type


class AdapterBase:
    """Base class for annotation-driven flat adapters."""

    _SCHEMA_CACHE: t.ClassVar[dict[type[AdapterBase], tuple[AdapterField, ...]]] = {}

    @classmethod
    def adapt(
        cls,
        line: DATA_FOR_ADAPT,
        parent_is_optional: bool = False,
        *,
        max_rows: int | None = None,
    ) -> FlatRows:
        """Adapt one input mapping; concrete subclasses provide the behavior.

        Args:
            line: Mapping to adapt.
            parent_is_optional: Whether missing child values may become ``None``.
            max_rows: Optional positive limit for the complete expansion.

        """
        raise NotImplementedError("Concrete adapters must implement `adapt`")

    @classmethod
    def iter_adapt(
        cls,
        line: DATA_FOR_ADAPT,
        parent_is_optional: bool = False,
        *,
        max_rows: int | None = None,
    ) -> Iterator[FlatRow]:
        """Lazily adapt one input mapping; concrete subclasses provide the behavior.

        Args:
            line: Mapping to adapt.
            parent_is_optional: Whether missing child values may become ``None``.
            max_rows: Optional positive limit for the complete expansion.

        Returns:
            An iterator over flat rows.

        """
        raise NotImplementedError("Concrete adapters must implement `iter_adapt`")

    @classmethod
    def _resolve_annotations(cls, target: type[AdapterBase]) -> dict[str, t.Any]:
        """Resolve annotations using the declaring module and local adapter scope."""
        module = sys.modules.get(target.__module__)
        base_module = sys.modules.get(AdapterBase.__module__)
        globalns: dict[str, object] = {}
        if base_module is not None:
            globalns.update(vars(base_module))
        if module is not None:
            globalns.update(vars(module))
        localns: dict[str, object] = {base.__name__: base for base in cls.__mro__}
        localns.update(vars(cls))
        try:
            return t.get_type_hints(
                target,
                globalns=globalns,
                localns=localns,
                include_extras=True,
            )
        except (NameError, TypeError) as exc:
            raise TypeResolutionError(f"Cannot resolve annotations for `{target.__name__}`") from exc

    @classmethod
    def _declared_annotations(cls) -> dict[str, t.Any]:
        """Collect inherited field annotations in declaration order."""
        annotations: dict[str, t.Any] = {}
        for target in reversed(cls.__mro__):
            if not isinstance(target, type) or target is object:
                continue
            declared = getattr(target, "__annotations__", {})
            if not declared:
                continue
            resolved = cls._resolve_annotations(target)
            for field_name, raw_annotation in declared.items():
                if field_name.startswith("_"):
                    continue
                annotations[field_name] = resolved.get(field_name, raw_annotation)
        return annotations

    @classmethod
    def _field_info(cls, field_name: str, annotation: t.Any) -> AdapterField:
        """Compile one annotation and its optional class-level metadata."""
        annotation, optional = _unwrap_optional(annotation)
        annotation, annotated_field = _unwrap_annotated(annotation)
        annotation, annotation_optional = _unwrap_optional(annotation)
        optional = optional or annotation_optional
        origin = t.get_origin(annotation)
        is_list = origin is list
        nested_annotation = t.get_args(annotation)[0] if is_list and t.get_args(annotation) else annotation
        nested_adapter = _adapter_type(nested_annotation)

        field_value = getattr(cls, field_name, None)
        output_name = field_value if isinstance(field_value, str) else field_name
        field = field_value if isinstance(field_value, Field) else annotated_field
        transformer = (
            t.cast(Callable[[object], object], field_value)
            if callable(field_value) and not isinstance(field_value, type)
            else None
        )
        if field is not None:
            transformer = None

        return AdapterField(
            field_name=field_name,
            output_name=output_name,
            annotation=annotation,
            optional=optional,
            is_list=is_list,
            adapter_type=nested_adapter,
            field=field,
            transformer=transformer,
        )

    @classmethod
    def adapter_fields(cls) -> Iterator[tuple[str, AdapterField]]:
        """Yield compiled fields in declaration order."""
        cached = cls._SCHEMA_CACHE.get(cls)
        if cached is None:
            cached = tuple(
                cls._field_info(name, annotation) for name, annotation in cls._declared_annotations().items()
            )
            cls._SCHEMA_CACHE[cls] = cached
        yield from ((field.field_name, field) for field in cached)

    @classmethod
    def schema(cls) -> dict[str, object]:
        """Return output column names mapped to their scalar annotations."""
        return {field.output_name: field.annotation for _, field in cls.adapter_fields()}


def convert_scalar(
    value: object,
    annotation: t.Any,
    field_name: str,
    optional: bool,
    parent_is_optional: bool,
) -> object:
    """Convert one scalar value according to an annotation.

    Missing values are accepted only for optional fields or optional parents.
    Conversion failures are normalized to ``ConversionError``.
    """
    annotation, annotation_optional = _unwrap_optional(annotation)
    if value is MISSING or value is None:
        if optional or annotation_optional or parent_is_optional:
            return None
        raise MissingFieldError(field_name, "FlatAdapter")

    if annotation in (t.Any, object):
        return value
    if isinstance(annotation, type) and type(value) is annotation:
        return value

    try:
        if annotation is bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            return str(value).strip().lower() not in {"", "0", "false", "no", "off"}
        if annotation is float:
            if isinstance(value, str):
                return float(value.replace(" ", "").replace(",", "."))
            if isinstance(value, (int, float)):
                return float(value)
            return float(str(value))
        if annotation is int:
            if isinstance(value, (int, float)):
                return int(value)
            return int(str(value))
        if annotation is str:
            return str(value)
        if annotation is datetime.datetime:
            return parse(str(value))
        if annotation is datetime.date:
            return parse(str(value)).date()
        if annotation is type(None) and str(value) == "N/A":
            return None
        if isinstance(annotation, type):
            return annotation(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ConversionError(field_name, annotation, value) from exc

    raise ConversionError(field_name, annotation, value)
