# Promotion Notes

This document is a release-time checklist and draft messaging. It is not a
claim that the package is production-ready before CI and the public contract
are stable.

## English launch draft

**Title:** Flatten nested Python mappings into database-ready rows

`flat-adapter` turns typed nested mappings into deterministic flat rows. It
supports scalar conversion, optional fields, custom source paths, nested
adapters, and Cartesian expansion of list-valued relationships.

```bash
uv add flat-adapter
```

The first release focuses on a small synchronous core with no database or web
framework dependency. Contributions and real-world ETL examples are welcome.

Suggested channels:

- PyPI project page and GitHub release
- Python forums and community newsletters
- Reddit communities focused on Python, ETL, and data engineering
- LinkedIn and engineering blogs with a benchmark-backed example

## Русский анонс

**Заголовок:** Превращаем вложенные структуры Python в плоские строки для БД

`flat-adapter` преобразует типизированные вложенные mapping в
детерминированный список плоских строк. Библиотека умеет приводить scalar-типы,
обрабатывать optional-поля, извлекать значения по путям, разворачивать
вложенные adapters и строить декартово произведение списков.

```bash
uv add flat-adapter
```

Первая версия — небольшой синхронный core без зависимости от БД и web-фреймворков.
Будут полезны примеры реальных ETL-сценариев и обратная связь по контракту
пустых списков, коллизий ключей и совместимости типов.

Предлагаемые каналы:

- PyPI и GitHub Release
- Telegram-чаты и русскоязычные Python-сообщества
- Habr и личный технический блог
- LinkedIn и профессиональные data engineering-сообщества

## Release checklist

1. Green CI on Python 3.10–3.13.
2. Confirm package metadata, license, version, and repository links.
3. Configure PyPI and TestPyPI trusted publishers for the `Release` workflow.
4. Run `Release` manually with `target=testpypi` and smoke-test the package.
5. Run `Release` manually with `target=pypi` after the TestPyPI gate passes.
6. Publish the first PyPI release with a changelog and migration notes.
7. Attach the same runnable example to English and Russian announcements.
8. Track installation feedback, failed examples, and requested input models.
