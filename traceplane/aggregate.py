import sys
import json
import csv
from collections import defaultdict
import statistics
import multiprocessing
from functools import partial

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

try:
    from tdigest import TDigest
    HAS_TDIGEST = True
except ImportError:
    HAS_TDIGEST = False

from .convert import get_actual_path, read_input
from .flatten import flatten_dict
from .query import matches_where
from .parser import parse_where

def _process_chunk_aggregate(chunk, is_flattened, flatten_sep, parsed_where, by_fields, sum_fields, avg_fields, min_fields, max_fields, p_fields):
    # Process a chunk of items for aggregation in a worker process
    from collections import defaultdict
    from .parser import evaluate
    
    local_groups = {}
    
    def to_float(val):
        if val is None or val == '': return None
        try: return float(val)
        except ValueError: return None

    for line_no, raw_obj in chunk:
        if is_flattened:
            dicts = [raw_obj]
        else:
            dicts = flatten_dict(raw_obj, sep=flatten_sep)
            
        for d in dicts:
            matched = True
            for ast in parsed_where:
                if not evaluate(ast, d):
                    matched = False
                    break
            if not matched:
                continue
                
            key = tuple(str(d.get(f, '')) for f in by_fields)
            
            if key not in local_groups:
                local_groups[key] = {
                    'count': 0,
                    'sums': defaultdict(float),
                    'counts': defaultdict(int),
                    'mins': {},
                    'maxs': {},
                    'p_vals': defaultdict(list)
                }
                
            g = local_groups[key]
            g['count'] += 1
            
            fields_to_sum = set(sum_fields + avg_fields)
            for f in fields_to_sum:
                val = to_float(d.get(f))
                if val is not None:
                    g['sums'][f] += val
                    g['counts'][f] += 1
                    
            for f in min_fields:
                val = to_float(d.get(f))
                if val is not None:
                    if f not in g['mins'] or val < g['mins'][f]:
                        g['mins'][f] = val
                        
            for f in max_fields:
                val = to_float(d.get(f))
                if val is not None:
                    if f not in g['maxs'] or val > g['maxs'][f]:
                        g['maxs'][f] = val
                        
            for f in p_fields:
                val = to_float(d.get(f))
                if val is not None:
                    g['p_vals'][f].append(val)

    return local_groups

def aggregate(input_paths, output_path, by_fields_str, count=False, sum_fields=None, avg_fields=None,
              min_fields=None, max_fields=None, p50_fields=None, p95_fields=None, p99_fields=None,
              to_json=False, ndjson_out=False, tsv=False, flatten_sep='.', where_filters=None):

    from .convert import resolve_input_paths, get_chained_input

    actual_paths = resolve_input_paths(input_paths)

    by_fields = [f.strip() for f in by_fields_str.split(',')] if by_fields_str else []
    sum_fields = sum_fields or []
    avg_fields = avg_fields or []
    min_fields = min_fields or []
    max_fields = max_fields or []
    p50_fields = p50_fields or []
    p95_fields = p95_fields or []
    p99_fields = p99_fields or []

    parsed_where = []
    if where_filters:
        parsed_where = [parse_where(w) for w in where_filters]

    def _matches(d):
        from .parser import evaluate
        for ast in parsed_where:
            if not evaluate(ast, d):
                return False
        return True

    p_fields = list(set(p50_fields + p95_fields + p99_fields))

    groups = {}

    iterator, is_flattened = get_chained_input(actual_paths)

    chunk_size = 5000
    def chunk_generator(iterator):
        chunk = []
        for item in iterator:
            chunk.append(item)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    chunks = chunk_generator(iterator)
    worker_func = partial(_process_chunk_aggregate, is_flattened=is_flattened, flatten_sep=flatten_sep,
                          parsed_where=parsed_where, by_fields=by_fields, sum_fields=sum_fields,
                          avg_fields=avg_fields, min_fields=min_fields, max_fields=max_fields, p_fields=p_fields)

    pool = multiprocessing.Pool()
    result_iterator = pool.imap_unordered(worker_func, chunks)

    if HAS_TQDM and output_path != '-':
        result_iterator = tqdm(result_iterator, desc="Aggregating chunks", unit="chunk")

    # Merge logic
    for local_groups in result_iterator:
        for key, lg in local_groups.items():
            if key not in groups:
                groups[key] = {
                    'count': 0,
                    'sums': defaultdict(float),
                    'counts': defaultdict(int),
                    'mins': {},
                    'maxs': {},
                    'p_vals': {}
                }
                if HAS_TDIGEST:
                    for f in p_fields:
                        groups[key]['p_vals'][f] = TDigest()
                else:
                    for f in p_fields:
                        groups[key]['p_vals'][f] = []

            g = groups[key]
            g['count'] += lg['count']

            for f in set(sum_fields + avg_fields):
                if f in lg['sums']:
                    g['sums'][f] += lg['sums'][f]
                    g['counts'][f] += lg['counts'][f]

            for f in min_fields:
                if f in lg['mins']:
                    if f not in g['mins'] or lg['mins'][f] < g['mins'][f]:
                        g['mins'][f] = lg['mins'][f]

            for f in max_fields:
                if f in lg['maxs']:
                    if f not in g['maxs'] or lg['maxs'][f] > g['maxs'][f]:
                        g['maxs'][f] = lg['maxs'][f]

            for f in p_fields:
                if f in lg['p_vals']:
                    if HAS_TDIGEST:
                        for val in lg['p_vals'][f]:
                            g['p_vals'][f].update(val)
                    else:
                        g['p_vals'][f].extend(lg['p_vals'][f])

    pool.close()
    pool.join()

    # Compile results
    results = []
    
    # Calculate percentiles properly
    def percentile(data, p):
        if HAS_TDIGEST and isinstance(data, TDigest):
            if data.n == 0: return None
            return data.percentile(p * 100)
        else:
            if not data: return None
            data.sort()
            k = (len(data) - 1) * p
            f = int(k)
            c = int(k) + 1 if int(k) < len(data) - 1 else f
            if f == c:
                return data[f]
            return data[f] + (k - f) * (data[c] - data[f])

    for key, g in groups.items():
        row = {}
        for i, field in enumerate(by_fields):
            row[field] = key[i]
            
        if count:
            row['count'] = g['count']
            
        for f in sum_fields:
            row[f'sum_{f}'] = g['sums'][f]
            
        for f in avg_fields:
            if g['counts'][f] > 0:
                row[f'avg_{f}'] = g['sums'][f] / g['counts'][f]
            else:
                row[f'avg_{f}'] = None
                
        for f in min_fields:
            row[f'min_{f}'] = g['mins'].get(f)
            
        for f in max_fields:
            row[f'max_{f}'] = g['maxs'].get(f)
            
        for f in p50_fields:
            row[f'p50_{f}'] = percentile(g['p_vals'][f], 0.50)
        for f in p95_fields:
            row[f'p95_{f}'] = percentile(g['p_vals'][f], 0.95)
        for f in p99_fields:
            row[f'p99_{f}'] = percentile(g['p_vals'][f], 0.99)
            
        results.append(row)
        
    out_f = sys.stdout if output_path == '-' else open(output_path, 'w', encoding='utf-8', newline='')
    
    try:
        if to_json:
            json.dump(results, out_f, indent=2)
            out_f.write('\n')
        elif ndjson_out:
            for r in results:
                out_f.write(json.dumps(r) + '\n')
        else:
            if results:
                header = list(results[0].keys())
                delimiter = '	' if tsv else ','
                writer = csv.DictWriter(out_f, fieldnames=header, delimiter=delimiter)
                writer.writeheader()
                for r in results:
                    writer.writerow({k: ('' if v is None else v) for k, v in r.items()})
    finally:
        if out_f is not sys.stdout:
            out_f.close()
