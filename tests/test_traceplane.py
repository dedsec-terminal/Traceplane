import os
import pytest
from traceplane.flatten import flatten_dict, unflatten_dict, split_key
from traceplane.query import matches_where

def test_split_key():
    assert split_key("user.name", ".") == ["user", "name"]
    assert split_key("user..name", ".") == ["user..name"]
    assert split_key("a.b..c.d", ".") == ["a", "b..c", "d"]

def test_flattening():
    d = {"user.name": "bob", "user": {"name": "alice"}}
    flat = flatten_dict(d, sep=".")
    assert len(flat) == 1
    f = flat[0]
    assert f["user..name"] == "bob"
    assert f["user.name"] == "alice"
    
    unflat = unflatten_dict(f, sep=".")
    assert unflat["user.name"] == "bob"
    assert unflat["user"]["name"] == "alice"

def test_arrays():
    d = {"tags": ["a", "b"], "conn": [{"ip": "1.1"}, {"ip": "2.2"}]}
    flat = flatten_dict(d, sep=".", array_sep=";")
    assert len(flat) == 1
    f = flat[0]
    assert f["tags"] == "a;b"
    assert f["conn.0.ip"] == "1.1"
    assert f["conn.1.ip"] == "2.2"

def test_where():
    d = {"user.name": "alice", "status": "200"}
    assert matches_where(d, ["status=200"])
    assert not matches_where(d, ["status=404"])
    assert matches_where(d, ["user.name~ali"])
    assert not matches_where(d, ["user.name~bob"])

def test_missing_fields_type_preservation():
    d = {"num": 42, "bool": True, "null": None, "str": "hello"}
    flat = flatten_dict(d)[0]
    csv_row = {k: str(v) if v is not None else "" for k, v in flat.items()}
    unflat = unflatten_dict(csv_row)
    assert unflat["num"] == 42
    assert unflat["bool"] is True
    assert unflat["str"] == "hello"
    assert "null" not in unflat

def run_tests():
    print("Running self-tests...")
    test_split_key()
    test_flattening()
    test_arrays()
    test_where()
    test_missing_fields_type_preservation()
    print("All tests passed.")
