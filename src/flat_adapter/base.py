from __future__ import annotations

import datetime
import typing as t

DATA_FOR_ADAPT = dict[str, object] | None

from sys import version_info
from types import ModuleType, UnionType

from dateutil.parser import parse

PYTHON_MINOR_WITH_OLD_TYPING = 8

# hints
ADOPTED_DATA = t.OrderedDict[str, object]
ADOPTED_DATA_AS_LIST = list[ADOPTED_DATA]

MISSING = object()

if version_info.minor >= PYTHON_MINOR_WITH_OLD_TYPING:
    get_origin: t.Callable = t.get_origin
    get_args: t.Callable = t.get_args
else:
    from adapters.typing_3_dot_7 import get_args, get_origin

# В новом формате type hints из версии 3.10+, используется types.UnionType, для случаев 'int | None'
UNION_TYPES = {t.Union, UnionType}

HINT_CONVERTERS = {
    datetime.date: lambda v: parse(v).date(),
    datetime.datetime: lambda v: parse(v),
    t.ForwardRef("timestamp"): lambda v: parse(v).timestamp(),
}

VALUE_STR_AS_NONE = {"N/A"}


class AdapterField(t.NamedTuple):
    """
    Свойства поля flat-адаптера.
    """

    name: str
    is_optional: bool = False
    is_list: bool = False
    adapter: AdapterBase | None = None
    func: t.Callable | None = None
    types_to: list[type] | None = None


class AdapterBase:
    """
    Базовый класс для flat-адаптеров.
    """

    @classmethod
    def adapt(
        cls,
        line: DATA_FOR_ADAPT,
        parent_is_optional: bool = False,
    ) -> ADOPTED_DATA | ADOPTED_DATA_AS_LIST:
        raise NotImplementedError("Необходима реализация `adapt` метода класса")

    @classmethod
    def _annotated_as_optional(cls, field_type: type) -> bool:
        origin = get_origin(field_type)
        args = get_args(field_type)

        if origin in UNION_TYPES and type(None) in args:
            return True

        return False

    @classmethod
    def _annotated_as_list(cls, field_type: type) -> bool:
        if not cls._annotated_as_optional(field_type):
            return get_origin(field_type) == list

        return any(cls._annotated_as_list(a) for a in get_args(field_type))

    @classmethod
    def _isadapterclass(cls, args: type) -> bool:
        return any(issubclass(c if type(c) == type else type(c), AdapterBase) for c in args)

    @classmethod
    def _getadapterclass(cls, *args: type | AdapterBase) -> AdapterBase | None:
        for a in args:
            if cls._isadapterclass(a):
                return a

            if cls._annotated_as_optional(a) or cls._annotated_as_list(a):
                return cls._getadapterclass(*get_args(a))

        return None

    @classmethod
    def _get_real_type(cls, type_name: str) -> type:
        # попытка найти ссылку на класс по его названию
        from sys import modules as sysmodules

        def modules() -> t.Generator[tuple[str, ModuleType], None, None]:
            module_name = cls.__module__

            # сначала ищем в модуле текущего класса
            yield module_name, sysmodules[module_name]

            for mname, module in sysmodules.items():
                if mname == module_name:
                    continue
                yield mname, module

        # теперь ищем во всех доступных модулях
        for _, module in modules():
            target = getattr(module, type_name, None)
            if target:
                return target

        raise AttributeError(
            f"Не удалось найти ссылку на класс `{type_name}` из схемы {cls.__name__}",
        )

    @classmethod
    def _get_types_to(cls, field_type: type | str) -> list[type]:
        origin, args = get_origin(field_type), get_args(field_type)

        if cls._annotated_as_optional(field_type) or cls._annotated_as_list(field_type):
            return [
                cls._get_types_to(a)[0] for a in args if not cls._isadapterclass(a) or not isinstance(a, type(None))
            ]

        if origin is not None:
            return [origin]

        return [field_type]

    @classmethod
    def _field_info(cls, field_name: str, field_type: type | str) -> AdapterField:
        if isinstance(field_type, str):
            field_type = cls._get_real_type(field_type)

        field_value = getattr(cls, field_name, field_name)

        return AdapterField(
            name=field_value if isinstance(field_value, str) else field_name,
            is_optional=cls._annotated_as_optional(field_type),
            is_list=cls._annotated_as_list(field_type),
            adapter=cls._getadapterclass(field_type),
            func=field_value if callable(field_value) else None,
            types_to=cls._get_types_to(field_type),
        )

    @classmethod
    def _convert_value(  # noqa: PLR0911, PLR0912 Too many return statements (10 > 6), Too many branches (16 > 12)
        cls,
        value: t.Any,
        field: AdapterField,
        parent_is_optional: bool = False,
    ) -> t.Any:
        if value is None or value is MISSING:
            if parent_is_optional:
                return None

            if field.is_optional and type(None) in field.types_to:
                return None

            raise ValueError(
                f"Поле `{field.name}` в схеме `{cls.__name__}` является обязательным но значение не задано!",
            )

        for typ in field.types_to:
            if type(value) == typ:
                return value

            if isinstance(typ, str):
                typ = cls._get_real_type(typ)  # noqa: PLW2901 `for` loop variable `typ` overwritten by assignment target

            if typ is bool:
                return cls._to_bool(value)

            if typ is float:
                return cls._to_float(value)

            try:
                if typ in HINT_CONVERTERS:
                    return HINT_CONVERTERS[typ](value)
                return typ(value)
            except (ValueError, TypeError):
                if value is None:
                    if typ == int:
                        return 0

                    if typ == bool:
                        return False

            if typ is type(None) and isinstance(value, str) and value in VALUE_STR_AS_NONE:
                return None

        raise ValueError(
            f"Поле `{cls.__name__}:{field.name}` невозможно привести к типу(-ам) {field.types_to} значение `{value}`",
        )

    @staticmethod
    def _to_float(value: t.Any) -> float | None:
        if value is None:
            # насчет float для Импала не уверен, но оставил.. пока..
            return value

        if isinstance(value, float):
            return value

        if isinstance(value, int):
            return float(value)

        value = str(value)
        value = value.replace(" ", "")
        value = value.replace(",", ".")
        return float(value)

    @staticmethod
    def _to_bool(value: t.Any) -> bool | None:
        if value is None:
            # Impala поддерживает наличие NULL в булевых столбцах,
            # равно как и pandas в виде column.astype("boolean")
            return value

        if isinstance(value, bool):
            return value

        if isinstance(value, float | int):
            return bool(value)

        value = str(value).lower()
        return value not in {"", "false", "0", "no"}

    @classmethod
    def type_hints(cls) -> t.Generator[tuple[str, type | str], None, None]:
        exclusion = {"object", "AdapterBase", "FlatAdapter"}
        mro = (k for k in cls.__mro__ if k.__name__ not in exclusion)

        proceeded = set()
        for klass in mro:
            for kls_name, kls in t.get_type_hints(klass).items():
                if kls_name in proceeded:
                    # поле уже было отдано в дочернем классе
                    continue

                if kls_name in klass.__annotations__:
                    yield kls_name, kls
                    proceeded.add(kls_name)

    @classmethod
    def adapter_fields(cls) -> t.Generator[tuple[str, AdapterField], None, None]:
        for field_name, field_type in cls.type_hints():
            field = cls._field_info(field_name, field_type)
            yield field_name, field

    @classmethod
    def schema(cls) -> dict:
        result = {}
        for field_name, field in cls.adapter_fields():
            if field.adapter:
                result = {**result, **field.adapter.schema()}
            else:
                result[field_name] = field.types_to[0]
        return result
