import json
import tempfile
from traceplane.aggregate import aggregate

def test_aggregate():
    data = [
        {"user": "alice", "score": 10},
        {"user": "alice", "score": 20},
        {"user": "bob", "score": 5},
    ]
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(data, f)
        temp_name = f.name
        
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as out_f:
        out_name = out_f.name

    aggregate(temp_name, out_name, by_fields_str="user", count=True, sum_fields=["score"], avg_fields=["score"], to_json=True)
    
    with open(out_name, 'r') as f:
        res = json.load(f)
        
    assert len(res) == 2
    alice = next(r for r in res if r['user'] == 'alice')
    assert alice['count'] == 2
    assert alice['sum_score'] == 30.0
    assert alice['avg_score'] == 15.0
    
    bob = next(r for r in res if r['user'] == 'bob')
    assert bob['count'] == 1
    assert bob['sum_score'] == 5.0
    assert bob['avg_score'] == 5.0
