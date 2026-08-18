import sys
import csv
import json
import tempfile

from .flatten import flatten_dict, unflatten_dict
from .query import apply_filters, matches_where

def get_actual_path(input_path):
    if input_path == '-':
        temp = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        for line in sys.stdin:
            temp.write(line)
        temp.close()
        return temp.name
    return input_path

def get_open_func(file_path):
    if file_path.endswith('.gz'):
        import gzip
        return gzip.open
    elif file_path.endswith('.bz2'):
        import bz2
        return bz2.open
    elif file_path.endswith('.xz'):
        import lzma
        return lzma.open
    return open

def read_input(file_path):
    open_func = get_open_func(file_path)
    with open_func(file_path, 'rt', encoding='utf-8') as f:
        first_char = ""
        while True:
            c = f.read(1)
            if not c:
                break
            if c.strip():
                first_char = c
                break
                
    if first_char == '[':
        with open_func(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
            return ((i+1, obj) for i, obj in enumerate(data)), False
    elif first_char == '{':
        def _gen():
            with open_func(file_path, 'rt', encoding='utf-8') as f2:
                first_line = f2.readline()
                try:
                    obj = json.loads(first_line)
                    yield (1, obj)
                    line_no = 2
                    for line in f2:
                        line = line.strip()
                        if not line:
                            line_no += 1
                            continue
                        try:
                            yield (line_no, json.loads(line))
                        except json.JSONDecodeError as e:
                            print(f"Warning: Skipping malformed JSON at line {line_no}: {e}", file=sys.stderr)
                        line_no += 1
                except json.JSONDecodeError:
                    f2.seek(0)
                    try:
                        data = json.load(f2)
                        for i, obj in enumerate(data):
                            yield (i+1, obj)
                    except json.JSONDecodeError as e:
                        print(f"Error reading JSON: {e}", file=sys.stderr)
        return _gen(), False
    else:
        def _gen_csv():
            with open_func(file_path, 'rt', encoding='utf-8') as f2:
                is_tsv = file_path.endswith('.tsv') or file_path.endswith('.tsv.gz')
                reader = csv.DictReader(f2, delimiter='	' if is_tsv else ',')
                for i, row in enumerate(reader, start=2):
                    yield (i, row)
        return _gen_csv(), True

def resolve_input_paths(input_paths):
    import glob
    actual_paths = []
    if isinstance(input_paths, str):
        input_paths = [input_paths]
    for p in input_paths:
        if p == '-': actual_paths.append(get_actual_path(p))
        else: actual_paths.extend(glob.glob(p) or [p])
    return actual_paths

def get_chained_input(actual_paths):
    from itertools import chain
    iterators = []
    is_flat_overall = False
    for i, p in enumerate(actual_paths):
        it, flat = read_input(p)
        if i == 0:
            is_flat_overall = flat
        iterators.append(it)
    return chain(*iterators), is_flat_overall

def convert(input_paths, output_path, to_json=False, ndjson_out=False, tsv=False, yaml_out=False,
            fields=None, exclude_fields=None, flatten_sep='.', array_sep=';', explode_arrays=False,
            where_filters=None, dedup=False, schema_file=None, preserve_strings=None,
            keep_as_string=False, null_value='', strict=False, limit=None, offset=None, sample=None):
            
    actual_paths = resolve_input_paths(input_paths)
    
    schema = {}
    if schema_file:
        with open(schema_file, 'r', encoding='utf-8') as sf:
            if schema_file.endswith('.yaml') or schema_file.endswith('.yml'):
                import yaml
                schema = yaml.safe_load(sf)
            else:
                schema = json.load(sf)
    
    preserve_strings = preserve_strings or []
    
    columns = set()
    needs_two_passes = not (to_json or ndjson_out or yaml_out)
    
    if needs_two_passes:
        iterator, is_flattened = get_chained_input(actual_paths)
        for line_no, raw_obj in iterator:
            if is_flattened:
                flat_dicts = [raw_obj]
            else:
                flat_dicts = flatten_dict(raw_obj, sep=flatten_sep, array_sep=array_sep, explode_arrays=explode_arrays)
                
            for d in flat_dicts:
                if not matches_where(d, where_filters):
                    continue
                d = apply_filters(d, fields, exclude_fields)
                columns.update(d.keys())
                
    header = sorted(list(columns)) if columns else []

    out_f = sys.stdout if output_path == '-' else open(output_path, 'w', encoding='utf-8', newline='')
    output_count = 0
    match_count = 0
    
    try:
        if yaml_out:
            try:
                import yaml
            except ImportError:
                print("Error: PyYAML is not installed. Please install with: pip install traceplane[yaml]", file=sys.stderr)
                sys.exit(1)
                
        writer = None
        if needs_two_passes:
            delimiter = '	' if tsv else ','
            writer = csv.DictWriter(out_f, fieldnames=header, delimiter=delimiter)
            writer.writeheader()
            
        seen_hashes = set()
        all_objects = []
        
        iterator, is_flattened = get_chained_input(actual_paths)
        for line_no, raw_obj in iterator:
            if is_flattened:
                flat_dicts = [raw_obj]
            else:
                flat_dicts = flatten_dict(raw_obj, sep=flatten_sep, array_sep=array_sep, explode_arrays=explode_arrays)
                
            for d in flat_dicts:
                if not matches_where(d, where_filters):
                    continue
                
                if sample is not None:
                    import random
                    if random.random() > sample:
                        continue
                
                match_count += 1
                if offset is not None and match_count <= offset:
                    continue
                
                d = apply_filters(d, fields, exclude_fields)
                
                if dedup:
                    h = hash(frozenset((k, str(v)) for k, v in d.items()))
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)
                    
                if not needs_two_passes:
                    try:
                        out_obj = unflatten_dict(
                            d, sep=flatten_sep, schema=schema,
                            preserve_strings=preserve_strings,
                            keep_as_string=keep_as_string, null_value=null_value,
                            line_no=line_no, strict=strict
                        )
                    except ValueError as e:
                        print(f"Error: {e}", file=sys.stderr)
                        sys.exit(1)
                    if ndjson_out:
                        out_f.write(json.dumps(out_obj) + '\n')
                    else:
                        all_objects.append(out_obj)
                else:
                    writer.writerow({k: d.get(k, '') for k in header})
                
                output_count += 1
                if limit is not None and output_count >= limit:
                    break
            else:
                continue
            break
                    
        if to_json:
            json.dump(all_objects, out_f, indent=2)
            out_f.write('\n')
        elif yaml_out:
            yaml.dump(all_objects, out_f, sort_keys=False)
            
        return output_count
            
    finally:
        if out_f is not sys.stdout:
            out_f.close()
