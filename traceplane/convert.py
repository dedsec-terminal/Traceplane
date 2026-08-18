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

def read_input(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        first_char = ""
        while True:
            c = f.read(1)
            if not c:
                break
            if c.strip():
                first_char = c
                break
                
    if first_char == '[':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data, False
    elif first_char == '{':
        def _gen():
            with open(file_path, 'r', encoding='utf-8') as f2:
                first_line = f2.readline()
                try:
                    obj = json.loads(first_line)
                    yield obj
                    line_no = 2
                    for line in f2:
                        line = line.strip()
                        if not line:
                            line_no += 1
                            continue
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError as e:
                            print(f"Warning: Skipping malformed JSON at line {line_no}: {e}", file=sys.stderr)
                        line_no += 1
                except json.JSONDecodeError:
                    f2.seek(0)
                    try:
                        yield json.load(f2)
                    except json.JSONDecodeError as e:
                        print(f"Error reading JSON: {e}", file=sys.stderr)
        return _gen(), False
    else:
        def _gen_csv():
            with open(file_path, 'r', encoding='utf-8') as f2:
                is_tsv = file_path.endswith('.tsv')
                reader = csv.DictReader(f2, delimiter='	' if is_tsv else ',')
                for row in reader:
                    yield row
        return _gen_csv(), True

def convert(input_path, output_path, to_json=False, ndjson_out=False, tsv=False, yaml_out=False,
            fields=None, exclude_fields=None, flatten_sep='.', array_sep=';', explode_arrays=False,
            where_filters=None, dedup=False):
            
    actual_path = get_actual_path(input_path)
    
    columns = set()
    needs_two_passes = not (to_json or ndjson_out or yaml_out)
    
    if needs_two_passes:
        iterator, is_flattened = read_input(actual_path)
        for raw_obj in iterator:
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
        
        iterator, is_flattened = read_input(actual_path)
        for raw_obj in iterator:
            if is_flattened:
                flat_dicts = [raw_obj]
            else:
                flat_dicts = flatten_dict(raw_obj, sep=flatten_sep, array_sep=array_sep, explode_arrays=explode_arrays)
                
            for d in flat_dicts:
                if not matches_where(d, where_filters):
                    continue
                d = apply_filters(d, fields, exclude_fields)
                
                if dedup:
                    h = hash(frozenset((k, str(v)) for k, v in d.items()))
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)
                    
                if not needs_two_passes:
                    out_obj = unflatten_dict(d, sep=flatten_sep)
                    if ndjson_out:
                        out_f.write(json.dumps(out_obj) + '\n')
                    else:
                        all_objects.append(out_obj)
                else:
                    writer.writerow({k: d.get(k, '') for k in header})
                    
        if to_json:
            json.dump(all_objects, out_f, indent=2)
            out_f.write('\n')
        elif yaml_out:
            yaml.dump(all_objects, out_f, sort_keys=False)
            
    finally:
        if out_f is not sys.stdout:
            out_f.close()
