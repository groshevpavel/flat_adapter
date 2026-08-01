# flat-adapter

`flat-adapter` превращает вложенные отображения в детерминированный набор
плоских строк для ETL-процессов и загрузки в таблицы БД.

## Быстрый старт

```python
from flat_adapter import FlatAdapter


class ItemAdapter(FlatAdapter):
    item_id: int
    quantity: int


class OrderAdapter(FlatAdapter):
    order_id: int
    items: list[ItemAdapter]


rows = OrderAdapter.adapt(
    {
        "order_id": "1001",
        "items": [
            {"item_id": "10", "quantity": "2"},
            {"item_id": "20", "quantity": "1"},
        ],
    }
)
```

Результат:

```python
[
    {"order_id": 1001, "item_id": 10, "quantity": 2},
    {"order_id": 1001, "item_id": 20, "quantity": 1},
]
```

## Контракт v0.1

- Вход — `Mapping[str, object]` с вложенными mapping и списками.
- Результат всегда `list[dict[str, object]]`.
- Несколько вложенных списков образуют декартово произведение.
- Порядок входных данных сохраняется.
- Неизвестные входные ключи игнорируются.
- Отсутствующие обязательные поля, ошибки преобразования, неверная форма
  вложенных данных и коллизии выходных ключей вызывают типизированные исключения.
- Пустой или `None` список сохраняет родительскую строку, заполняя поля дочернего adapter значениями `None`.
- `None` у обязательного вложенного объекта считается ошибкой.
- Dataclass, Pydantic, БД и HTTP API пока не входят в границы библиотеки.

## Настройка Field без `cast`

Для проектов со строгой типизацией используйте `typing.Annotated`:

```python
from typing import Annotated

from flat_adapter import Field, FlatAdapter


class CustomerAdapter(FlatAdapter):
    customer_id: Annotated[int, Field(source="payload.customer_id")]
    display_name: Annotated[str, Field(source="payload.name", default="Unknown")]
```

Старый вариант `name: str = Field(...)` продолжает работать во время выполнения,
но `Annotated` предпочтителен для проектов с `mypy --strict`.

## Производительность и ограничение строк

Семь-десять уровней вложенных adapters обычно не являются проблемой. Основной
риск связан с декартовым произведением списков. Для длин списков `L1`, `L2`, ...
число строк может расти как `product(max(1, len(Li)))`, а все строки результата
материализуются в памяти.

Используйте `max_rows`, чтобы прервать слишком большое разворачивание заранее:

```python
rows = OrderAdapter.adapt(payload, max_rows=10_000)
```

Запустить локальные benchmark-сценарии можно командой:

```bash
uv run python benchmarks/flatten_benchmark.py
```

## Разработка

Проект использует [uv](https://docs.astral.sh/uv/) для окружения, зависимостей
и lock-файла.

```bash
uv sync
uv run pre-commit install
uv run pre-commit run --all-files
uv run pytest --cov=flat_adapter --cov-report=term-missing
uv run ruff check src tests
uv run mypy --strict src tests
uv build
uv run twine check dist/*
```

## Структура пакета

```text
src/flat_adapter/  Код библиотеки
tests/unit/        Поведенческие unit-тесты
docs/              Английское и русское руководство и материалы продвижения
benchmarks/        Ручные сценарии проверки производительности
```

Архитектурные решения описаны в [CONTEXT.md](../CONTEXT.md), технический долг —
в [TECHDEBT.md](../TECHDEBT.md).

English version: [README.en.md](README.en.md).

## Версионирование

Релизы следуют Semantic Versioning. Пока пакет младше `1.0.0`, minor-релиз может
содержать документированное изменение контракта; patch-релизы остаются
обратно совместимыми исправлениями. Пользовательские изменения фиксируются в
`CHANGELOG.md`.
