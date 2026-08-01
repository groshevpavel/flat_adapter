"""Unit tests for the basic FlatAdapter facade."""

from flat_adapter import FlatAdapter


class UserAdapter(FlatAdapter):
    """Declare a required identifier and an aliased field."""

    user_id: int
    name: str = "full_name"


class OptionalAdapter(FlatAdapter):
    """Declare one optional scalar field."""

    value: int | None


def test_adapt_returns_one_flat_row_and_applies_alias() -> None:
    """Return one converted row and apply a class-level output alias."""
    result = UserAdapter.adapt({"user_id": "7", "name": "Alice"})

    assert result == [{"user_id": 7, "full_name": "Alice"}]


def test_unknown_input_keys_are_ignored() -> None:
    """Ignore input keys that are not declared by the adapter."""
    assert UserAdapter.adapt({"user_id": 7, "name": "Alice", "ignored": True}) == [{"user_id": 7, "full_name": "Alice"}]


def test_missing_optional_scalar_becomes_none() -> None:
    """Convert a missing optional scalar to None."""
    assert OptionalAdapter.adapt({}) == [{"value": None}]
