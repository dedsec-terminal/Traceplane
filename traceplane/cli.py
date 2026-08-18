import argparse
import sys
from .convert import convert
from .query import stats
from .aggregate import aggregate

def main():
    parser = argparse.ArgumentParser(description="Traceplane: CLI tool for structured log/data conversion")
    subparsers = parser.add_subparsers(dest='command', help='Sub-commands')

    # Convert
    convert_parser = subparsers.add_parser('convert', help='Convert files')
    convert_parser.add_argument('input', nargs='+', help='Input file path(s)')
    convert_parser.add_argument('-o', '--output', default='-', help='Output file path (default: stdout)')
    convert_parser.add_argument('--tsv', action='store_true', help='Output TSV')
    convert_parser.add_argument('--to-json', action='store_true', help='Output JSON array')
    convert_parser.add_argument('--ndjson-out', action='store_true', help='Output NDJSON')
    convert_parser.add_argument('--yaml', action='store_true', help='Output YAML')
    convert_parser.add_argument('--fields', nargs='+', help='Fields to include (post-flatten names)')
    convert_parser.add_argument('--exclude-fields', nargs='+', help='Fields to exclude')
    convert_parser.add_argument('--flatten-sep', default='.', help='Separator for flattened keys (default: .)')
    convert_parser.add_argument('--array-sep', default=';', help='Separator for array of primitives (default: ;)')
    convert_parser.add_argument('--explode-arrays', action='store_true', help='Create one row per array element')
    convert_parser.add_argument('--where', action='append', help='Filter: field=value or field~substring')
    convert_parser.add_argument('--dedup', action='store_true', help='Deduplicate rows')
    convert_parser.add_argument('--schema', help='Schema file (JSON or YAML) mapping dotted field -> type')
    convert_parser.add_argument('--preserve-strings', nargs='+', default=[], help='Fields to preserve as strings (no type coercion)')
    convert_parser.add_argument('--keep-as-string', action='store_true', help='Keep string types unless strictly typed')
    convert_parser.add_argument('--null-value', default='', help='Value to treat as null')
    convert_parser.add_argument('--strict', action='store_true', help='Fail on schema type errors')
    convert_parser.add_argument('--limit', type=int, help='Limit number of output rows')
    convert_parser.add_argument('--offset', type=int, help='Skip number of output rows')
    convert_parser.add_argument('--sample', type=float, help='Sample fraction (e.g. 0.1 for 10%%)')

    # Stats
    stats_parser = subparsers.add_parser('stats', help='Get field statistics')
    stats_parser.add_argument('input', help='Input file path')
    stats_parser.add_argument('--field', required=True, help='Field name to analyze')

    # Aggregate
    agg_parser = subparsers.add_parser('aggregate', help='Aggregate data')
    agg_parser.add_argument('input', nargs='+', help='Input file path(s)')
    agg_parser.add_argument('-o', '--output', default='-', help='Output file path (default: stdout)')
    agg_parser.add_argument('--by', help='Comma-separated fields to group by')
    agg_parser.add_argument('--count', action='store_true', help='Count rows in group')
    agg_parser.add_argument('--sum', action='append', help='Sum of field')
    agg_parser.add_argument('--avg', action='append', help='Average of field')
    agg_parser.add_argument('--min', action='append', help='Minimum of field')
    agg_parser.add_argument('--max', action='append', help='Maximum of field')
    agg_parser.add_argument('--p50', action='append', help='p50 of field')
    agg_parser.add_argument('--p95', action='append', help='p95 of field')
    agg_parser.add_argument('--p99', action='append', help='p99 of field')
    agg_parser.add_argument('--tsv', action='store_true', help='Output TSV')
    agg_parser.add_argument('--to-json', action='store_true', help='Output JSON array')
    agg_parser.add_argument('--ndjson-out', action='store_true', help='Output NDJSON')
    agg_parser.add_argument('--where', action='append', help='Filter data before aggregating')

    # Schema
    schema_parser = subparsers.add_parser('schema', help='Infer schema from file')
    schema_parser.add_argument('--infer', required=True, help='Input file path to infer schema from')
    schema_parser.add_argument('-o', '--output', default='-', help='Output file path (default: stdout)')

    # Run
    run_parser = subparsers.add_parser('run', help='Run from config file')
    run_parser.add_argument('--config', default='traceplane.yaml', help='Config file path')

    # Self-test
    parser.add_argument('--self-test', action='store_true', help='Run built-in test suite')

    args = parser.parse_args()

    if args.self_test:
        from tests.test_traceplane import run_tests
        run_tests()
        sys.exit(0)

    if args.command == 'convert':
        count = convert(args.input, args.output, to_json=args.to_json, ndjson_out=args.ndjson_out,
                tsv=args.tsv, yaml_out=args.yaml, fields=args.fields, exclude_fields=args.exclude_fields,
                flatten_sep=args.flatten_sep, array_sep=args.array_sep, explode_arrays=args.explode_arrays,
                where_filters=args.where, dedup=args.dedup, schema_file=args.schema,
                preserve_strings=args.preserve_strings, keep_as_string=args.keep_as_string,
                null_value=args.null_value, strict=args.strict, limit=args.limit,
                offset=args.offset, sample=args.sample)
        if count == 0:
            sys.exit(2)
    elif args.command == 'stats':
        stats(args.input, args.field)
    elif args.command == 'aggregate':
        count = aggregate(args.input, args.output, by_fields_str=args.by, count=args.count,
                  sum_fields=args.sum, avg_fields=args.avg, min_fields=args.min,
                  max_fields=args.max, p50_fields=args.p50, p95_fields=args.p95, p99_fields=args.p99,
                  to_json=args.to_json, ndjson_out=args.ndjson_out, tsv=args.tsv,
                  where_filters=args.where)
        if count == 0:
            sys.exit(2)
    elif args.command == 'schema':
        from .schema import infer_schema
        infer_schema(args.infer, args.output)
    elif args.command == 'run':
        import os, json
        config_path = args.config
        if not os.path.exists(config_path):
            if os.path.exists('traceplane.json'):
                config_path = 'traceplane.json'
            else:
                print(f"Error: config file {config_path} not found", file=sys.stderr)
                sys.exit(1)
                
        config = {}
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                import yaml
                config = yaml.safe_load(f)
            else:
                config = json.load(f)
                
        cmd = config.get('command')
        if cmd == 'convert':
            convert(config.get('input', []), config.get('output', '-'),
                    to_json=config.get('to_json', False), ndjson_out=config.get('ndjson_out', False),
                    tsv=config.get('tsv', False), yaml_out=config.get('yaml', False),
                    fields=config.get('fields'), exclude_fields=config.get('exclude_fields'),
                    flatten_sep=config.get('flatten_sep', '.'), array_sep=config.get('array_sep', ';'),
                    explode_arrays=config.get('explode_arrays', False),
                    where_filters=config.get('where'), dedup=config.get('dedup', False),
                    schema_file=config.get('schema'), preserve_strings=config.get('preserve_strings'),
                    keep_as_string=config.get('keep_as_string', False), null_value=config.get('null_value', ''))
        elif cmd == 'aggregate':
            aggregate(config.get('input', []), config.get('output', '-'),
                      by_fields_str=config.get('by'), count=config.get('count', False),
                      sum_fields=config.get('sum'), avg_fields=config.get('avg'),
                      min_fields=config.get('min'), max_fields=config.get('max'),
                      p50_fields=config.get('p50'), p95_fields=config.get('p95'), p99_fields=config.get('p99'),
                      to_json=config.get('to_json', False), ndjson_out=config.get('ndjson_out', False),
                      tsv=config.get('tsv', False), where_filters=config.get('where'))
        else:
            print(f"Error: Unknown command '{cmd}' in config", file=sys.stderr)
            sys.exit(1)
    else:
        if not args.self_test:
            parser.print_help()

if __name__ == '__main__':
    main()
