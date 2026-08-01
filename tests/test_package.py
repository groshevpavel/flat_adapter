"""Smoke tests for the public package API."""

from flat_adapter import AdapterBase, AdapterField, Field, FlatAdapter


def test_public_package_exports_are_available() -> None:
    """Expose the documented adapter classes and field metadata."""
    assert issubclass(FlatAdapter, AdapterBase)
    assert AdapterField.__name__ == "AdapterField"
    assert Field.__name__ == "Field"
