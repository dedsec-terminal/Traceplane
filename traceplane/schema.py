import sys
import json
from .convert import get_chained_input, resolve_input_paths
from .flatten import flatten_dict

def infer_schema(input_paths, output_path, sample_size=1000):
    actual_paths = resolve_input_paths(input_paths)
    iterator, is_flattened = get_chained_input(actual_paths)
    
    types = {}
    
    def _get_type(val):
        if val is None or val == '': return None
        if isinstance(val, bool): return 'boolean'
        if isinstance(val, int): return 'int'
        if isinstance(val, float): return 'float'
        if isinstance(val, str):
            v = val.lower()
            if v in ('true', 'false'): return 'boolean'
            try:
                if '.' in val:
                    float(val)
                    return 'float'
                else:
                    int(val)
                    return 'int'
            except ValueError:
                return 'string'
        return 'string'
        
    def _merge_type(current, new):
        if not current: return new
        if not new: return current
        if current == 'string' or new == 'string': return 'string'
        if current == 'float' and new == 'int': return 'float'
        if current == 'int' and new == 'float': return 'float'
        if current != new: return 'string'
        return current

    count = 0
    for line_no, raw_obj in iterator:
        if is_flattened:
            flat_dicts = [raw_obj]
        else:
            flat_dicts = flatten_dict(raw_obj)
            
        for d in flat_dicts:
            for k, v in d.items():
                t = _get_type(v)
                if t:
                    types[k] = _merge_type(types.get(k), t)
        
        count += 1
        if count >= sample_size:
            break
            
    out_f = sys.stdout if output_path == '-' else open(output_path, 'w', encoding='utf-8')
    try:
        json.dump(types, out_f, indent=2)
        if out_f is sys.stdout:
            out_f.write('\n')
    finally:
        if out_f is not sys.stdout:
            out_f.close()
