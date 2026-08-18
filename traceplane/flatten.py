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

def unflatten_dict(d, sep='.'):
    result = {}
    for k, v in d.items():
        if v == '' or v is None:
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
