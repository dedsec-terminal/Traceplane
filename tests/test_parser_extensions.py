from traceplane.parser import parse_where, evaluate
def test_arithmetic():
    ast = parse_where("a + b = 10")
    assert evaluate(ast, {"a": 4, "b": 6})
    assert not evaluate(ast, {"a": 4, "b": 5})

    ast = parse_where("a * b > 20")
    assert evaluate(ast, {"a": 5, "b": 5})

def test_functions():
    ast = parse_where("length(name) > 3")
    assert evaluate(ast, {"name": "alice"})
    assert not evaluate(ast, {"name": "bob"})

    ast = parse_where("lower(name) = john")
    assert evaluate(ast, {"name": "JOHN"})
