# Changelog

All notable changes to this project will be documented here.

## [Unreleased]

- Defined the first row-based transformation contract.
- Added typed adapter exceptions.
- Added `Annotated[T, Field(...)]` configuration for strict-typing projects
  without `cast`.
- Added deep-nesting tests, local flattening benchmarks, and the `max_rows`
  fail-fast guard for Cartesian expansion.
- Added unit coverage for scalar conversion, custom fields, nested mappings,
  Cartesian list expansion, empty values, and key collisions.
- Added uv-based CI, packaging checks, and bilingual documentation drafts.
