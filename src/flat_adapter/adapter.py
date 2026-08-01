from __future__ import annotations

import logging
import typing as t

from collections import OrderedDict
from functools import reduce
from itertools import product

from .base import ADOPTED_DATA, ADOPTED_DATA_AS_LIST, DATA_FOR_ADAPT, AdapterBase, AdapterField


class FlatAdapter(AdapterBase):
    """
    Адаптер для выпрямления данных изначально имеющих вложенную структуру. Планируется для использования в загрузках
    данных Опоросса.

    Назначение: создание из данных с вложенной структурой csv-подобной(плоской) структуры для импорта через ЕРП

    Извлекает данные из вложенной структуры в плоских, используя
    аннотации переменных класса в качестве шаблона извлечения данных.

    Пример класса-шаблона:

    class StatsAnswer(FlatAdapter):
        qid: str = "question_id"
        time: int = "response_dttm"
        type: str = "response_type"
        comment: str | None = "response_comment"
        data: t.List[StatsAnswerData]

    По данному классу, будет производится извлечение данных из вложенной структуры.
    Переменная класса `qid` это название ключа во вложенной структуре, по которому будет извлечено данное
    значение для переменной класса, заданное как `question_id` является псевдонимом для результирующего поля,
    то есть, результат извлечения данных из ключа `qid` будет помещен в ключ `question_id`.
    Если значение переменной класса не указано в псевдониме или используется
    и данные помещаются в поле с таким же названием.

    В случае если переменная класса содержит аннотацию с применением typing.Optional (см. поле comment),
    тогда, поле помечается как "необязательное", и в случае его отсутствия в исходных данных, возвращается None

    Внутри класса-схемы, ссылка на другой класс может быть обернута typing.Optional,
    в этом случае весь шаблон помечается как "необязательный", то есть, в случае отсутствия данных,
    либо, получив пустых данных по указанному ключу,
    будет возвращен объект содержащий все поля шаблона заполненные None

    Значение переменной класса может быть вызываемым(callable) объектом,
    в этом случае для данных будет произведен вызов этого callable-объекта.

    Примеры:

    lines = [
        {
            "data": [
                {
                    "name": "item",
                    "value": 5,
                }
            ],
            "qid": "53330",
            "skipped": False,
            "time": "2022-12-05 14:35:51",
            "type": "csi",
        },
        {
            "data": [
                {
                    "name": "item",
                    "qid": "168627",
                    "value": "Обязательность",
                }
            ],
            "qid": "53332",
            "skipped": False,
            "time": "2022-12-05 14:36:11",
            "type": "opened",
        },
    ]

    assert StatsAnswer.adapt(lines) == OrderedDict(
        [
            ("question_id", ["53330", "53332"]),
            ("response_dttm", ["2022-12-05 14:35:51", "2022-12-05 14:36:11"]),
            ("response_type", ["csi", "opened"]),
            ("response_comment", [None, None]),
            (
                "data",
                [
                    [{"name": "item", "value": 5}],
                    [{"name": "item", "qid": "168627", "value": "Обязательность"}],
                ],
            ),
        ]
    )
    """

    __ADAPTER_MAPPING__: t.ClassVar[dict[type, dict[str, AdapterField]]] = {}

    @classmethod
    def _get_adapter_map(cls) -> dict[str, AdapterField]:
        adapter_map = cls.__ADAPTER_MAPPING__.get(cls, {})

        if not adapter_map:
            for field_name, field in cls.adapter_fields():
                adapter_map[field_name] = field

            cls.__ADAPTER_MAPPING__[cls] = adapter_map

        return adapter_map

    @classmethod
    def _flat_reducer(
        cls,
        first: list[dict],
        second: list[dict],
    ) -> ADOPTED_DATA_AS_LIST:
        if isinstance(first, dict):
            first = [first]

        result = []
        for f, s in product(first, second):
            if isinstance(s, list):
                result.extend(cls._flat(f, s))
            else:
                keys_intersection = set(f.keys()).intersection(s.keys())
                if keys_intersection:
                    raise ValueError(
                        "Опасность потери данных! "
                        f"Дублирование ключа(-ей) {keys_intersection} в разных сущностях адаптера {cls.__name__}",
                    )
                result.append(OrderedDict({**f, **s}))

        return result

    @classmethod
    def _flat(cls, *args: ADOPTED_DATA | ADOPTED_DATA_AS_LIST) -> ADOPTED_DATA | ADOPTED_DATA_AS_LIST:
        start = OrderedDict()

        for a in args:
            if isinstance(a, dict):
                if diff := set(start.keys()).intersection(set(a.keys())):
                    raise ValueError(
                        f"Дублирование ключа(-ей) {diff}, опасность потери данных! {start=};{a=}",
                    )
                start.update(a)

        args = [a for a in args if isinstance(a, list)]
        if not args:
            logging.warning(f"WARNING! {cls.__name__} возвращает только словарь {start=}")
            return start

        return reduce(cls._flat_reducer, args, start)

    @classmethod
    def adapt(  # noqa: PLR0912 Too many branches (18 > 12)
        cls,
        line: DATA_FOR_ADAPT,
        parent_is_optional: bool = False,
    ) -> ADOPTED_DATA | ADOPTED_DATA_AS_LIST:
        main = OrderedDict()
        to_flat = []

        for field_name, field in cls._get_adapter_map().items():
            value = None

            if line:
                if not field.is_optional and not field.func and field_name not in line:
                    # поле не обрабатывается? единственное для поля?
                    raise KeyError(
                        f"Нет обязательного поля `{field_name}` в данных, по схеме `{cls.__name__}`",
                    )

                value = line.get(field_name, None)

            if field.func:
                try:
                    value = field.func(line, field_name, field) if isinstance(field.func, Field) else field.func(line)
                except Exception as e:
                    if not field.is_optional:
                        raise e

            if not field.adapter:
                main[field.name] = cls._convert_value(value, field, parent_is_optional)
                continue

            if field.adapter:
                if field.is_list:
                    if not value:
                        # адаптер вызван для создания пустого набора
                        value = [field.adapter.adapt(None, parent_is_optional=True)]
                        to_flat.append(value)
                    else:
                        value = field.adapter.adapt(value, parent_is_optional=field.is_optional)
                else:
                    value = field.adapter.adapt(value, parent_is_optional=field.is_optional)

                if isinstance(value, (list | tuple | set)):
                    to_flat.append(value)
                else:
                    diff = set(main.keys()).intersection(value)
                    if diff:
                        raise KeyError(
                            "Опасность перезаписи данных! "
                            f"Дубли ключей {diff} при добавлении из поля {field_name} схемы `{cls.__name__}`",
                        )
                    main.update(value)

        if not to_flat:
            return main

        return cls._flat(main, *to_flat)

    @classmethod
    def _adapt_values_list(cls, field: AdapterField, value: list[t.Any]) -> ADOPTED_DATA_AS_LIST:
        result = []
        for v in value:
            try:
                result.append(field.adapter.adapt(v))
            except KeyError as e:
                skip_if_not_exist = getattr(field.adapter, "__skip_if_not_exist__", None)
                if skip_if_not_exist:
                    not_exist_field_name = e.args[1]
                    if not_exist_field_name in skip_if_not_exist:
                        continue
                raise

        value = result
        del result
        return value


class Field:
    """
    Параметры одного поля flat-адаптера.

    Указание специфических условий извлечения данных.

    :param source: Название ключа из которого будут извлекаться данные
    :param delimiter: Разделитель для source - если указан то производится последовательное извлечение в глубину
    :param default: Значение которое будет возвращено в случае если значение отсутствует или не задано
    :param prepare_data_func: Функция для преобразования исходных данных

    """

    def __init__(
        self,
        source: str | None = None,
        delimiter: str = "",
        default: t.Any | None = None,
        prepare_data_func: t.Callable[[t.Any], t.Any] | None = None,
    ) -> None:
        self.source = source
        self.source_delimiter = delimiter
        self.default = default
        self.prepare_data_func = prepare_data_func

    def __call__(  # noqa: PLR0911 Too many return statements (7 > 6)
        self,
        line: dict | None,
        field_name: str,
        field: AdapterField,
    ) -> t.Any:
        if line is None:
            return None

        if self.source is not None and self.source_delimiter in self.source:
            result = reduce(
                lambda v, k: v.get(k, {}),
                self.source.split(self.source_delimiter),
                line,
            )

            if not result and field.is_optional and self.default is not None:
                if callable(self.default):
                    return self.default()
                return self.default

            return result or None

        try:
            data = line[self.source] if self.source else line[field_name]
            if self.prepare_data_func:
                data = self.prepare_data_func(data)

            return data
        except KeyError:
            if self.default is not None:
                if callable(self.default):
                    return self.default()
                return self.default

            raise KeyError(
                f"Поле `{self.source or field_name}` не обнаружено в \n{str(line)[:100]}...\n{self}",
            ) from None


field = Field
