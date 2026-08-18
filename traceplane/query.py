from .parser import parse_where, evaluate

_where_cache = {}

def matches_where(d: dict, where_filters: list) -> bool:
    if not where_filters:
        return True
    for flt in where_filters:
        if flt not in _where_cache:
            # Fallback to old simple format if parsing fails (for backward compatibility)
            # Actually, parse_where handles 'a=b' correctly!
            _where_cache[flt] = parse_where(flt)
            
        ast = _where_cache[flt]
        if not evaluate(ast, d):
            return False
    return True

def apply_filters(d: dict, fields: list, exclude_fields: list) -> dict:
    if fields:
        d = {k: v for k, v in d.items() if k in fields}
    if exclude_fields:
        d = {k: v for k, v in d.items() if k not in exclude_fields}
    return d

def stats(input_path, field, flatten_sep='.'):
    import sys
    from .convert import get_actual_path, read_input
    from .flatten import flatten_dict
    
    actual_path = get_actual_path(input_path)
    iterator, is_flattened = read_input(actual_path)
    
    counts = {}
    total = 0
    for raw_obj in iterator:
        if is_flattened:
            dicts = [raw_obj]
        else:
            dicts = flatten_dict(raw_obj, sep=flatten_sep)
            
        for d in dicts:
            if field in d:
                val = str(d[field])
                counts[val] = counts.get(val, 0) + 1
                total += 1
                
    if total == 0:
        print(f"No records found with field '{field}'")
        return
        
    print(f"{'Value':<30} | {'Count':<8} | {'Percentage':<10}")
    print("-" * 55)
    for val, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total) * 100
        val_str = val if len(val) <= 30 else val[:27] + "..."
        print(f"{val_str:<30} | {count:<8} | {pct:.1f}%")
