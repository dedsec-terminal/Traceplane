# Traceplane

Traceplane is a production-grade, lightweight, and minimal-dependency Python CLI tool for converting, analyzing, and reshaping structured log and data files (JSON, NDJSON, CSV, TSV). It is purpose-built for real-world messy data.

## Features

- **Deep Flattening**: Nested JSON objects are flattened into dot-notation columns (`user.address.city`).
- **Key-Collision Safety**: If literal keys already contain dots (`{"user.name": "bob"}`), Traceplane carefully escapes them (`user..name`) to avoid silent data corruption.
- **Type & Schema Preservation**: Smart handling of strings vs numbers. Automatically deduce schema, and prevent implicit coercion of zero-padded strings or phone numbers when converting between formats.
- **Power Filtering (`--where`)**: Query your data using a robust, dependency-free expression engine.
- **Lightning Aggregations**: Group by fields and calculate statistics (`--count`, `--sum`, `--avg`, `--p99`) across huge datasets.
- **Streaming & Performance**: Processes massive NDJSON logs line-by-line. Natively and transparently supports reading `.gz`, `.bz2`, and `.xz` files.
- **Exploration**: Quickly dive into huge datasets using `--limit`, `--offset`, and `--sample`.

## Installation

Install Traceplane directly via pip:

```bash
pip install git+https://github.com/dedsec-terminal/Traceplane.git
# or locally:
pip install .
```

For optional capabilities, you can install the optional dependencies:
```bash
pip install traceplane[yaml,parquet,sqlite,progress]
```

## Quick Start

Convert a nested JSON file to a flat CSV:
```bash
traceplane convert data.json -o flat.csv
```

Convert it back to JSON perfectly reconstructing the nested structure:
```bash
traceplane convert flat.csv -o roundtrip.json --to-json
```

Filter your logs using SQL-like expressions and sample 10% of them:
```bash
traceplane convert "logs/*.ndjson.gz" -o subset.csv --where "status >= 400" --sample 0.1
```

Get summary statistics on request latencies by path:
```bash
traceplane aggregate access.log --by "request.path" --count --avg "response.time" --p99 "response.time"
```

## Command Reference

### `traceplane convert`

The primary command for converting, filtering, and projecting data.

**Basic Options:**
- `input`: Input file(s). Supports glob patterns (`*.json`) and transparently handles `.gz`, `.bz2`, and `.xz` files. Use `-` for stdin.
- `-o`, `--output`: Output file path (default: stdout).
- `--to-json`: Output as a JSON array.
- `--ndjson-out`: Output as newline-delimited JSON (NDJSON).
- `--tsv`: Output as TSV (Tab-Separated Values).
- `--yaml`: Output as YAML (requires `traceplane[yaml]`).

**Data Reshaping & Exploration:**
- `--fields F1,F2`: Comma-separated list of fields to include.
- `--exclude-fields F1,F2`: Comma-separated list of fields to exclude.
- `--where EXPR`: Filter rows. Can be specified multiple times (implicitly ANDed).
- `--dedup`: Deduplicate identical rows before outputting.
- `--limit N`: Limit the number of output rows.
- `--offset N`: Skip the first `N` matched rows.
- `--sample P`: Randomly sample a fraction of matched rows (e.g., `0.1` for 10%).

**Type & Schema Options:**
- `--schema FILE`: Path to a JSON or YAML schema file dictating types (`int`, `float`, `boolean`, `string`) for specific fields.
- `--preserve-strings F1,F2`: Force these specific fields to remain strings to prevent leading zeros from disappearing (e.g. `phone_number`, `user.id`).
- `--keep-as-string`: Global flag to treat all parsed fields as strings unless dictated by schema.
- `--null-value STR`: The literal string representation for nulls (defaults to an empty string).
- `--strict`: By default, schema type coercion failures emit a warning to `stderr` and keep the original string. Enable `--strict` to abort the program (Exit Code 1) immediately upon a type coercion error.

### `traceplane aggregate`

Group data and calculate statistics quickly. 

- `input`: Input file(s).
- `--by FIELD1,FIELD2`: Comma-separated fields to group by.
- `--count`: Count rows per group.
- `--sum FIELD`, `--avg FIELD`, `--min FIELD`, `--max FIELD`: Mathematical aggregations.
- `--p50 FIELD`, `--p95 FIELD`, `--p99 FIELD`: Percentile calculations.
- Output formatting flags: `--to-json`, `--ndjson-out`, `--tsv`.
- Filter before aggregating: `--where EXPR`.

### `traceplane schema`

Quickly infer a schema from a sample of your data.
- `--infer FILE`: Deduce the schema (reads up to the first 1000 rows).
- `-o`, `--output`: Where to save the schema (JSON format).

```bash
traceplane schema --infer data.csv -o schema.json
traceplane convert data.csv --schema schema.json --to-json
```

### `traceplane run`

Execute predefined pipelines from a configuration file. By default, it looks for `traceplane.yaml` or `traceplane.json` in the current directory.
- `--config FILE`: Specify a different config file path.

Example `traceplane.yaml`:
```yaml
command: convert
input: ["raw_data/*.gz"]
output: clean.csv
where:
  - "valid = true"
fields:
  - id
  - timestamp
```

## The Expression Engine (`--where`)

Traceplane includes a robust, zero-dependency recursive descent expression parser. Evaluation is AST-based and **completely safe** from code injection (no `eval()` is used).

**Operators Supported:**
- Comparison: `=`, `!=`, `>`, `>=`, `<`, `<=`
- Strings: `~` (contains), `=~` (regex match)
- Presence: `exists`, `is_null`
- Sets: `in`, `not in` (e.g., `status in (200, 201)`)
- Logical: `AND`, `OR`, `NOT`, `(`, `)`

**Examples:**
```bash
# Basic comparison
traceplane convert ... --where "status != 200 AND path =~ '^/api/v1'"

# Check existence
traceplane convert ... --where "user.email exists AND metadata.deleted is_null"

# Parenthetical logic
traceplane convert ... --where "(latency > 1000 AND status = 500) OR method in ('DELETE', 'POST')"
```

## Exit Codes

Traceplane is built to integrate beautifully into bash scripts and automation:
- **0**: Success. Everything processed normally and rows were written.
- **1**: Error. Usually caused by invalid syntax, file read errors, or schema coercion failures under `--strict`.
- **2**: No Matches. The pipeline ran successfully, but zero rows were written to the output (often because `--where` filtered everything out).

## Development

```bash
# Run tests
pip install pytest
pytest tests/
```

## License

Traceplane is released under the MIT License. See [LICENSE](LICENSE) for details.
