import pytest
from traceplane.flatten import unflatten_dict

def test_unflatten_default_coercion():
    d = {"age": "42", "active": "true", "score": "3.14", "null_field": "null", "name": "bob"}
    res = unflatten_dict(d)
    assert res == {"age": 42, "active": True, "score": 3.14, "null_field": None, "name": "bob"}

def test_unflatten_keep_as_string():
    d = {"age": "42", "active": "true", "score": "3.14", "null_field": "null", "name": "bob"}
    res = unflatten_dict(d, keep_as_string=True)
    # Note: "null" becomes None only via implicit coercion, if kept as string, it's "null"
    assert res == {"age": "42", "active": "true", "score": "3.14", "null_field": "null", "name": "bob"}

def test_unflatten_preserve_strings_list():
    d = {"id": "007", "count": "5"}
    res = unflatten_dict(d, preserve_strings=["id"])
    assert res == {"id": "007", "count": 5}

def test_unflatten_schema():
    d = {"id": "007", "is_admin": "false", "score": "10"}
    schema = {
        "id": "string",
        "is_admin": "boolean",
        "score": "float"
    }
    res = unflatten_dict(d, schema=schema)
    assert res == {"id": "007", "is_admin": False, "score": 10.0}

def test_null_value():
    d = {"empty": "", "explicit_null": "NULL", "valid": "data"}
    res = unflatten_dict(d, null_value="NULL")
    # "empty" should be skipped because it's '' and not null_value
    assert "empty" not in res
    assert res["explicit_null"] is None
    assert res["valid"] == "data"

def test_null_value_empty_string():
    # If null_value is '', then '' becomes None, but since default null_value=''
    # and we skip None if it came from '' to preserve old behavior, it's omitted.
    d = {"empty": "", "valid": "data"}
    res = unflatten_dict(d, null_value="")
    assert "empty" not in res
    assert res["valid"] == "data"

def test_json_null_preservation():
    # If a value is genuinely None (from JSON), it should not be skipped anymore.
    d = {"null_field": None, "valid": "data"}
    res = unflatten_dict(d, null_value="")
    assert res["null_field"] is None
    assert res["valid"] == "data"
