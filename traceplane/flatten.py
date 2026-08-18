def escape_key(key: str, sep: str) -> str:
    return key.replace(sep, sep * 2)

def split_key(key: str, sep: str) -> list:
    parts = []
    current = []
    i = 0
    while i < len(key):
        if key[i:i+len(sep)] == sep:
            if key[i:i+len(sep)*2] == sep * 2:
                current.append(sep * 2)
                i += len(sep) * 2
            else:
                parts.append(''.join(current))
                current = []
                i += len(sep)
        else:
            current.append(key[i])
            i += 1
    parts.append(''.join(current))
    return parts

def unflatten_dict(d, sep='.', schema=None, preserve_strings=None, keep_as_string=False, null_value='', line_no=None, strict=False):
    if schema is None:
        schema = {}
    if preserve_strings is None:
        preserve_strings = []

    result = {}
    for k, v in d.items():
        is_explicit_null = False
        if isinstance(v, str) and v == null_value:
            v = None
            is_explicit_null = True

        # In original traceplane, empty string '' was skipped.
        # We preserve this behavior for CSV empty cells, but if it was explicitly
        # the null_value (which defaults to ''), it becomes None and we don't skip it.
        # However, to avoid breaking CSV -> JSON by adding `{"col": null}` everywhere,
        # we will skip `None` if `null_value == ''` and it was parsed from `''`.
        # Actually, let's keep it simple: if it's the null_value, it's None.
        if v == '' and not is_explicit_null:
            continue
            
        # We don't skip `v is None` anymore, so JSON -> JSON preserves `null`!
        # Except if null_value is '' and we just converted '' to None from CSV.
        # If the user wants to skip CSV empty cells, they shouldn't set null_value=''.
        # Wait, the prompt says default is empty. If default is '', then CSV '' becomes None.
        # Then we output `{"col": null}` for all empty CSV cells.
        # To preserve old behavior where empty CSV cells are omitted, let's omit `None` if it was from `''` by default?
        if v is None and is_explicit_null and null_value == '':
            continue

        parts = split_key(k, sep)
        current = result
        for i, part in enumerate(parts[:-1]):
            part = part.replace(sep * 2, sep)
            next_part = parts[i+1]
            if part not in current:
                if next_part.isdigit():
                    current[part] = {}
                else:
                    current[part] = {}
            current = current[part]
        
        last_part = parts[-1].replace(sep * 2, sep)
        
        if isinstance(v, str):
            field_type = schema.get(k)
            should_preserve = keep_as_string or (k in preserve_strings)
            
            if field_type == 'string':
                pass # keep as string
            elif field_type == 'int':
                try: v = int(v)
                except ValueError:
                    if strict:
                        raise ValueError(f"Line {line_no}: could not coerce '{k}' ('{v}') to int")
                    import sys
                    print(f"Warning: line {line_no} - could not coerce '{k}' ('{v}') to int", file=sys.stderr)
            elif field_type == 'float':
                try: v = float(v)
                except ValueError:
                    if strict:
                        raise ValueError(f"Line {line_no}: could not coerce '{k}' ('{v}') to float")
                    import sys
                    print(f"Warning: line {line_no} - could not coerce '{k}' ('{v}') to float", file=sys.stderr)
            elif field_type == 'boolean' or field_type == 'bool':
                v = v.lower() == 'true'
            elif not should_preserve:
                # Default implicit coercion
                if v.lower() == 'true':
                    v = True
                elif v.lower() == 'false':
                    v = False
                elif v.lower() in ('null', 'none'):
                    v = None
                else:
                    try:
                        if '.' in v:
                            v = float(v)
                        else:
                            v = int(v)
                    except ValueError:
                        pass
                    
        current[last_part] = v
        
    return _dicts_to_lists(result)

def _dicts_to_lists(obj):
    if isinstance(obj, dict):
        if obj and all(k.isdigit() for k in obj.keys()):
            indices = sorted([int(k) for k in obj.keys()])
            if indices == list(range(len(indices))):
                return [_dicts_to_lists(obj[str(i)]) for i in indices]
        return {k: _dicts_to_lists(v) for k, v in obj.items()}
    return obj

def flatten_dict(d, parent_key='', sep='.', array_sep=';', explode_arrays=False):
    if not isinstance(d, dict):
        return [{parent_key: d}] if parent_key else [{}]
        
    dicts = [{}]
    
    for k, v in d.items():
        escaped_k = escape_key(str(k), sep)
        new_key = f"{parent_key}{sep}{escaped_k}" if parent_key else escaped_k
        
        if isinstance(v, dict):
            sub_dicts = flatten_dict(v, new_key, sep, array_sep, explode_arrays)
            new_dicts = []
            for d1 in dicts:
                for d2 in sub_dicts:
                    d_copy = d1.copy()
                    d_copy.update(d2)
                    new_dicts.append(d_copy)
            dicts = new_dicts
            
        elif isinstance(v, list):
            if explode_arrays:
                if not v:
                    for d1 in dicts:
                        d1[new_key] = None
                else:
                    new_dicts = []
                    for item in v:
                        if isinstance(item, dict):
                            sub_dicts = flatten_dict(item, new_key, sep, array_sep, explode_arrays)
                        elif isinstance(item, list):
                            sub_dicts = [{new_key: str(item)}]
                        else:
                            sub_dicts = [{new_key: item}]
                            
                        for d1 in dicts:
                            for d2 in sub_dicts:
                                d_copy = d1.copy()
                                d_copy.update(d2)
                                new_dicts.append(d_copy)
                    dicts = new_dicts
            else:
                is_primitives = all(not isinstance(i, (dict, list)) for i in v)
                if is_primitives:
                    val = array_sep.join(str(i) for i in v)
                    for d1 in dicts:
                        d1[new_key] = val
                else:
                    sub_dicts = [{}]
                    for i, item in enumerate(v):
                        indexed_key = f"{new_key}{sep}{i}"
                        if isinstance(item, dict):
                            item_dicts = flatten_dict(item, indexed_key, sep, array_sep, explode_arrays)
                            new_sub_dicts = []
                            for sd1 in sub_dicts:
                                for sd2 in item_dicts:
                                    sd_copy = sd1.copy()
                                    sd_copy.update(sd2)
                                    new_sub_dicts.append(sd_copy)
                            sub_dicts = new_sub_dicts
                        else:
                            for sd1 in sub_dicts:
                                sd1[indexed_key] = item
                                
                    new_dicts = []
                    for d1 in dicts:
                        for d2 in sub_dicts:
                            d_copy = d1.copy()
                            d_copy.update(d2)
                            new_dicts.append(d_copy)
                    dicts = new_dicts
        else:
            for d1 in dicts:
                d1[new_key] = v
                
    return dicts
