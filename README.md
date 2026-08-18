# Traceplane

Traceplane is an installable Python CLI tool for converting and working with structured log/data files (JSON, NDJSON, CSV, TSV). It is purpose-built for real-world messy data.

## Features

- **Flattening**: Deeply nested JSON objects are flattened into dot-notation columns (`user.name`).
- **Key-Collision Safety**: If your literal keys already contain dots (e.g. `{"user.name": "bob"}`), Traceplane carefully escapes them to avoid silent data corruption.
- **Arrays**: Arrays of primitives are joined. Arrays of objects are indexed by default (`conn.0.ip`), with an `--explode-arrays` option.
- **Schema Drift**: When outputting CSV/TSV, it unions all discovered columns across the whole file. Missing values safely render as empty.
- **Streaming**: Processes NDJSON line-by-line, efficiently handling massive log files.
- **Stats & Filtering**: Supports deduplication, filtering by fields, grep-like value filtering, and generating frequency stats.

## Installation

```bash
pip install git+https://github.com/dedsec-terminal/Traceplane.git
# or locally:
pip install .
```

For YAML support:
```bash
pip install traceplane[yaml]
```

## Example

**Input (input.json):**
```json
{"user.name": "alice", "user": {"name": "bob"}, "tags": ["a", "b"]}
```

**Output (CSV):**
```csv
tags,user..name,user.name
a;b,alice,bob
```

Notice how `user.name` becomes `user..name` to safely round-trip back to JSON!

## Usage

```bash
# Convert JSON to CSV
traceplane convert input.json -o output.csv

# Convert back to JSON (round-trip)
traceplane convert output.csv -o roundtrip.json --to-json

# Filter and Deduplicate
traceplane convert huge_logs.ndjson -o filtered.csv --where "status_code=500" --dedup

# Get Field Stats
traceplane stats input.json --field status_code
```

## License

See [LICENSE](LICENSE) for details.
