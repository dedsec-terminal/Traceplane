import pytest
from traceplane.flatten import flatten_dict, unflatten_dict

def test_round_trip_basic():
    original = {"a": {"b": 1}, "c": [2, 3]}
    flat = flatten_dict(original)[0]
    unflat = unflatten_dict(flat)
    assert unflat == {"a": {"b": 1}, "c": "2;3"}  # Without explode_arrays, arrays are joined

def test_round_trip_explode_arrays():
    original = {"a": [{"b": 1}, {"b": 2}], "c": 3}
    flat_dicts = flatten_dict(original, explode_arrays=True)
    # Actually, unflatten_dict expects a single row dict, so it unflattens each row.
    unflat_list = [unflatten_dict(d) for d in flat_dicts]
    assert unflat_list == [{"a": {"b": 1}, "c": 3}, {"a": {"b": 2}, "c": 3}]

def test_round_trip_empty_object():
    original = {"a": {}, "b": 1}
    flat = flatten_dict(original)[0]
    unflat = unflatten_dict(flat)
    # flattening an empty object just omits it because it has no leaves
    assert unflat == {"b": 1}

def test_round_trip_empty_array():
    original = {"a": [], "b": 1}
    flat = flatten_dict(original, explode_arrays=True)
    assert flat == [{'a': None, 'b': 1}]
    unflat_list = [unflatten_dict(d) for d in flat]
    # traceplane converts None to None
    assert unflat_list == [{"a": None, "b": 1}]

def test_round_trip_deep_nesting():
    original = {"a": {"b": {"c": {"d": {"e": 5}}}}}
    flat = flatten_dict(original)[0]
    unflat = unflatten_dict(flat)
    assert unflat == original

def test_round_trip_mixed_types():
    original = {"a": [1, "two", False, None]}
    flat = flatten_dict(original)[0]
    # Joined to "1;two;False;None"
    assert flat["a"] == "1;two;False;None"

def test_round_trip_strict_type_coercion():
    flat = {"a": "foo"}
    with pytest.raises(ValueError, match="Line 1: could not coerce"):
        unflatten_dict(flat, schema={"a": "int"}, strict=True, line_no=1)
