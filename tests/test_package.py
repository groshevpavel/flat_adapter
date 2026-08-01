from flat_adapter import AdapterBase, AdapterField, Field, FlatAdapter


def test_public_package_exports_are_available() -> None:
    assert issubclass(FlatAdapter, AdapterBase)
    assert AdapterField.__name__ == "AdapterField"
    assert Field.__name__ == "Field"
