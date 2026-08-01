# Technical Debt Registry

| ID | Component | Priority | Description | Proposed Solution | Risk | Status |
|----|-----------|----------|-------------|-------------------|------|--------|
| TD-001 | tests | HIGH | The recovered adapter has no executable behavior tests. | Add focused unit tests for scalar conversion, optional fields, nested adapters, list expansion, defaults, and collision errors using RED-GREEN-REFACTOR. | Regressions and incorrect data loads can go unnoticed. | open |
| TD-002 | base.py | HIGH | Runtime type introspection and adapter discovery were recovered without tests; `_isadapterclass` and forward-reference handling need validation. | Specify supported annotation forms and replace fragile discovery with deterministic metadata/registration. | Valid schemas may fail at runtime or resolve the wrong class. | open |
| TD-003 | adapter.py | HIGH | Nested list flattening and duplicate-key handling are undocumented beyond an example in a docstring. | Write examples and tests that define row ordering, Cartesian expansion, empty lists, `None`, and collision semantics. | Silent row loss or data overwrites during ETL. | open |
| TD-004 | packaging | MEDIUM | PyPI metadata still contains placeholder project URLs and an initial alpha version. | Confirm ownership, repository URLs, license, versioning policy, and release checklist before publication. | Broken package metadata or an incorrect public release. | open |
| TD-005 | compatibility | MEDIUM | Python 3.10+ is declared, but the recovered prototype has not been verified across supported interpreters. | Add CI matrix for Python 3.10–3.13 and run the test/lint/type gates on each version. | Version-specific import or typing failures. | open |
