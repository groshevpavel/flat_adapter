"""Unit tests for nested adapters and Cartesian row expansion."""

import types
from typing import Any, cast

import pytest

from flat_adapter import (
    DuplicateFieldError,
    FlatAdapter,
    InvalidRowLimitError,
    InvalidShapeError,
    MissingFieldError,
    RowLimitExceeded,
)


class DetailsAdapter(FlatAdapter):
    """Declare fields for a nested details mapping."""

    name: str
    age: int


class ItemAdapter(FlatAdapter):
    """Declare fields for one list item."""

    item_id: int


class TagAdapter(FlatAdapter):
    """Declare fields for one list tag."""

    tag: str


class ParentAdapter(FlatAdapter):
    """Combine nested details, items, and tags."""

    parent_id: int
    details: DetailsAdapter | None
    items: list[ItemAdapter]
    tags: list[TagAdapter]


class RequiredDetailsParent(FlatAdapter):
    """Declare a parent with a required nested object."""

    details: DetailsAdapter


class LeftAdapter(FlatAdapter):
    """Declare the left side of a collision test."""

    value: int


class RightAdapter(FlatAdapter):
    """Declare the right side of a collision test."""

    value: int


class CollisionParent(FlatAdapter):
    """Combine nested adapters that intentionally collide."""

    left: LeftAdapter
    right: RightAdapter


class ForwardParent(FlatAdapter):
    """Declare a parent using a string forward reference."""

    child: "ForwardChild"


class ForwardChild(FlatAdapter):
    """Declare the target of the forward reference."""

    value: int


class VariantAdapter(FlatAdapter):
    """Declare one variant for the Cartesian-product test."""

    variant_id: int


class ChannelAdapter(FlatAdapter):
    """Declare one channel for the Cartesian-product test."""

    channel: str


class RegionAdapter(FlatAdapter):
    """Declare one region for the Cartesian-product test."""

    region: str


class ProductParentAdapter(FlatAdapter):
    """Combine three independent lists into a Cartesian product."""

    variants: list[VariantAdapter]
    channels: list[ChannelAdapter]
    regions: list[RegionAdapter]


def _make_deep_adapter(depth: int) -> tuple[type[FlatAdapter], dict[str, object]]:
    """Build a mixed mapping/list adapter and a matching input payload."""
    adapter: type[FlatAdapter] = type(
        "DeepLeafAdapter",
        (FlatAdapter,),
        {
            "__annotations__": {"value": int},
            "__doc__": "Declare the leaf of a deep adapter chain.",
        },
    )
    payload: dict[str, object] = {"value": "7"}

    for level in range(depth, 0, -1):
        field_name = f"level_{level}"
        is_list = level % 2 == 0
        annotation: object = types.GenericAlias(list, adapter) if is_list else adapter
        payload = {field_name: [payload] if is_list else payload}
        adapter = type(
            f"DeepLevel{level}Adapter",
            (FlatAdapter,),
            {
                "__annotations__": {field_name: annotation},
                "__doc__": f"Declare deep adapter level {level}.",
            },
        )

    return adapter, payload


DeepAdapter, DEEP_PAYLOAD = _make_deep_adapter(10)


def test_nested_lists_expand_using_a_deterministic_cartesian_product() -> None:
    """Expand two nested lists in stable Cartesian-product order."""
    result = ParentAdapter.adapt(
        {
            "parent_id": "1",
            "details": {"name": "parent", "age": "30"},
            "items": [{"item_id": "10"}, {"item_id": "20"}],
            "tags": [{"tag": "a"}, {"tag": "b"}],
        }
    )

    assert result == [
        {"parent_id": 1, "name": "parent", "age": 30, "item_id": 10, "tag": "a"},
        {"parent_id": 1, "name": "parent", "age": 30, "item_id": 10, "tag": "b"},
        {"parent_id": 1, "name": "parent", "age": 30, "item_id": 20, "tag": "a"},
        {"parent_id": 1, "name": "parent", "age": 30, "item_id": 20, "tag": "b"},
    ]


def test_empty_nested_list_preserves_parent_row_with_null_child_fields() -> None:
    """Preserve a parent row when a nested list is empty."""
    result = ParentAdapter.adapt(
        {
            "parent_id": 1,
            "details": {"name": "parent", "age": 30},
            "items": [],
            "tags": [{"tag": "a"}],
        }
    )

    assert result == [{"parent_id": 1, "name": "parent", "age": 30, "item_id": None, "tag": "a"}]


def test_none_nested_list_has_the_same_parent_preserving_semantics() -> None:
    """Treat a None nested list like an empty nested list."""
    result = ParentAdapter.adapt(
        {
            "parent_id": 1,
            "details": {"name": "parent", "age": 30},
            "items": None,
            "tags": [{"tag": "a"}],
        }
    )

    assert result == [{"parent_id": 1, "name": "parent", "age": 30, "item_id": None, "tag": "a"}]


def test_missing_required_nested_list_raises_typed_error() -> None:
    """Reject a missing required nested list."""
    with pytest.raises(MissingFieldError, match="items"):
        ParentAdapter.adapt({"parent_id": 1, "details": None, "tags": []})


def test_missing_optional_nested_object_fills_child_fields_with_none() -> None:
    """Fill missing optional nested object fields with None."""
    assert ParentAdapter.adapt({"parent_id": 1, "items": [], "tags": []}) == [
        {"parent_id": 1, "name": None, "age": None, "item_id": None, "tag": None}
    ]


def test_none_optional_nested_object_fills_child_fields_with_none() -> None:
    """Fill explicit None optional nested object fields with None."""
    result = ParentAdapter.adapt(
        {
            "parent_id": 1,
            "details": None,
            "items": [{"item_id": 10}],
            "tags": [{"tag": "a"}],
        }
    )

    assert result == [{"parent_id": 1, "name": None, "age": None, "item_id": 10, "tag": "a"}]


def test_none_required_nested_object_raises_typed_error() -> None:
    """Reject None for a required nested object."""
    with pytest.raises(MissingFieldError, match="details"):
        RequiredDetailsParent.adapt({"details": None})


def test_nested_sequence_must_be_a_list() -> None:
    """Reject tuple input for a list-valued nested field."""
    with pytest.raises(InvalidShapeError, match="items"):
        ParentAdapter.adapt(
            {
                "parent_id": 1,
                "details": {"name": "parent", "age": 30},
                "items": ("not", "a", "list"),
                "tags": [],
            }
        )


def test_nested_object_must_be_a_mapping() -> None:
    """Reject scalar input for a nested mapping field."""
    with pytest.raises(InvalidShapeError, match="details"):
        ParentAdapter.adapt(
            {
                "parent_id": 1,
                "details": "not-a-mapping",
                "items": [],
                "tags": [],
            }
        )


def test_set_is_rejected_as_an_unordered_nested_sequence() -> None:
    """Reject set input because its iteration order is not deterministic."""
    with pytest.raises(InvalidShapeError, match="items"):
        ParentAdapter.adapt(
            {
                "parent_id": 1,
                "details": {"name": "parent", "age": 30},
                "items": {("item", 1)},
                "tags": [],
            }
        )


def test_duplicate_nested_output_keys_raise_before_data_is_overwritten() -> None:
    """Reject duplicate nested keys instead of silently overwriting values."""
    with pytest.raises(DuplicateFieldError, match="value"):
        CollisionParent.adapt({"left": {"value": 1}, "right": {"value": 2}})


def test_forward_reference_is_resolved_from_the_declaring_module() -> None:
    """Resolve a string annotation from the declaring module."""
    assert ForwardParent.adapt({"child": {"value": "5"}}) == [{"value": 5}]


def test_ten_nested_mapping_and_list_levels_are_adapted() -> None:
    """Adapt a mixed mapping/list structure ten levels deep."""
    assert DeepAdapter.adapt(DEEP_PAYLOAD) == [{"value": 7}]


def test_three_nested_lists_produce_twenty_four_rows_in_order() -> None:
    """Expand list lengths two, three, and four into twenty-four rows."""
    result = ProductParentAdapter.adapt(
        {
            "variants": [{"variant_id": 1}, {"variant_id": 2}],
            "channels": [{"channel": "web"}, {"channel": "store"}, {"channel": "api"}],
            "regions": [
                {"region": "eu"},
                {"region": "us"},
                {"region": "apac"},
                {"region": "latam"},
            ],
        }
    )

    assert len(result) == 24
    assert result[0] == {
        "variant_id": 1,
        "channel": "web",
        "region": "eu",
    }
    assert result[-1] == {
        "variant_id": 2,
        "channel": "api",
        "region": "latam",
    }


def test_max_rows_allows_an_exact_result_size() -> None:
    """Return all rows when the result exactly reaches the configured limit."""
    result = ParentAdapter.adapt(
        {
            "parent_id": 1,
            "details": {"name": "parent", "age": 30},
            "items": [{"item_id": 10}, {"item_id": 20}],
            "tags": [{"tag": "a"}, {"tag": "b"}],
        },
        max_rows=4,
    )

    assert len(result) == 4


def test_max_rows_rejects_cartesian_expansion_before_returning_partial_rows() -> None:
    """Raise when Cartesian expansion would exceed the configured limit."""
    with pytest.raises(RowLimitExceeded, match="maximum of 3"):
        ParentAdapter.adapt(
            {
                "parent_id": 1,
                "details": {"name": "parent", "age": 30},
                "items": [{"item_id": 10}, {"item_id": 20}],
                "tags": [{"tag": "a"}, {"tag": "b"}],
            },
            max_rows=3,
        )


def test_max_rows_rejects_nested_list_accumulation() -> None:
    """Raise while a single nested list is accumulating too many rows."""
    with pytest.raises(RowLimitExceeded, match="maximum of 3"):
        ParentAdapter.adapt(
            {
                "parent_id": 1,
                "details": None,
                "items": [
                    {"item_id": 10},
                    {"item_id": 20},
                    {"item_id": 30},
                    {"item_id": 40},
                ],
                "tags": [],
            },
            max_rows=3,
        )


def test_max_rows_rejects_invalid_limits() -> None:
    """Reject zero and negative row limits."""
    with pytest.raises(InvalidRowLimitError, match="positive"):
        ParentAdapter.adapt({"parent_id": 1, "items": [], "tags": []}, max_rows=0)
    with pytest.raises(InvalidRowLimitError, match="positive"):
        ParentAdapter.adapt({"parent_id": 1, "items": [], "tags": []}, max_rows=-1)


def test_root_input_must_be_a_mapping() -> None:
    """Reject a root input that is not a mapping."""
    with pytest.raises(InvalidShapeError, match="mapping"):
        ParentAdapter.adapt(cast(Any, ["not", "a", "mapping"]))
