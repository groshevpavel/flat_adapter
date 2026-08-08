# Changelog

All notable changes to this project will be documented here.

## [0.2.0] - 2026-08-08

- Defined the first row-based transformation contract.
- Added typed adapter exceptions.
- Added `Annotated[T, Field(...)]` configuration for strict-typing projects
  without `cast`.
- Added deep-nesting tests, local flattening benchmarks, and the `max_rows`
  fail-fast guard for Cartesian expansion.
- Added lazy `iter_adapt()` row iteration while keeping `adapt()` as the eager
  list-returning API.
- Added unit coverage for scalar conversion, custom fields, nested mappings,
  Cartesian list expansion, empty values, and key collisions.
- Added uv-based CI, packaging checks, and bilingual documentation drafts.
