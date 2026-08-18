import pytest
from traceplane.query import matches_where

def test_matches_where_simple_equals():
    d = {"name": "alice", "age": 30}
    assert matches_where(d, ["name=alice"])
    assert not matches_where(d, ["name=bob"])

def test_matches_where_operators():
    d = {"age": 30, "status": "active", "count": 5}
    assert matches_where(d, ["age > 20"])
    assert matches_where(d, ["age >= 30"])
    assert matches_where(d, ["count < 10"])
    assert matches_where(d, ["status != inactive"])
    assert matches_where(d, ["status ~ act"])
    assert matches_where(d, ["status =~ ^a.*e$"])

def test_matches_where_boolean_logic():
    d = {"role": "admin", "age": 40}
    assert matches_where(d, ["role = admin AND age > 30"])
    assert matches_where(d, ["role = user OR age = 40"])
    assert matches_where(d, ["(role = user OR role = admin) AND age > 35"])

def test_matches_where_in_exists_isnull():
    d = {"role": "admin", "empty": ""}
    # in
    assert matches_where(d, ["role in admin,user"])
    assert matches_where(d, ["role not in guest,banned"])
    # exists
    assert matches_where(d, ["role exists"])
    assert not matches_where(d, ["missing exists"])
    # is_null
    assert matches_where(d, ["missing is_null"])

def test_matches_where_strings_with_spaces():
    d = {"name": "John Doe", "city": "New York"}
    assert matches_where(d, ["name = 'John Doe'"])
    assert matches_where(d, ['city = "New York"'])
