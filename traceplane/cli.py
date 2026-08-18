import argparse
import sys
from .convert import convert
from .query import stats

def main():
    parser = argparse.ArgumentParser(description="Traceplane: CLI tool for structured log/data conversion")
    subparsers = parser.add_subparsers(dest='command', help='Sub-commands')

    # Convert
    convert_parser = subparsers.add_parser('convert', help='Convert files')
    convert_parser.add_argument('input', help='Input file path')
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

    # Stats
    stats_parser = subparsers.add_parser('stats', help='Get field statistics')
    stats_parser.add_argument('input', help='Input file path')
    stats_parser.add_argument('--field', required=True, help='Field name to analyze')

    # Self-test
    parser.add_argument('--self-test', action='store_true', help='Run built-in test suite')

    args = parser.parse_args()

    if args.self_test:
        from tests.test_traceplane import run_tests
        run_tests()
        sys.exit(0)

    if args.command == 'convert':
        convert(args.input, args.output, to_json=args.to_json, ndjson_out=args.ndjson_out, tsv=args.tsv, yaml_out=args.yaml,
                fields=args.fields, exclude_fields=args.exclude_fields, flatten_sep=args.flatten_sep, 
                array_sep=args.array_sep, explode_arrays=args.explode_arrays,
                where_filters=args.where, dedup=args.dedup)
    elif args.command == 'stats':
        stats(args.input, args.field)
    else:
        if not args.self_test:
            parser.print_help()

if __name__ == '__main__':
    main()
