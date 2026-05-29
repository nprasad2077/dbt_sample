#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DB_PATH="$REPO_ROOT/data/DB/dbt_nba.duckdb"
REPORTS_DB="$REPO_ROOT/dbt_nba/reports/sources/nba/dbt_nba.duckdb"

# Check prerequisites
if [ -z "${POSTGRES_URL:-}" ]; then
  echo "ERROR: POSTGRES_URL environment variable is not set" >&2
  exit 1
fi

echo "==> Extracting from Postgres into DuckDB..."
mkdir -p "$(dirname "$DB_PATH")"
rm -f "$DB_PATH"
envsubst < "$REPO_ROOT/scripts/extract.sql" | duckdb "$DB_PATH"

echo "==> Running dbt build..."
cd "$REPO_ROOT/dbt_nba"
uv run --project "$REPO_ROOT" dbt deps --profiles-dir .
uv run --project "$REPO_ROOT" dbt build --profiles-dir .

echo "==> Copying database to reports..."
cp "$DB_PATH" "$REPORTS_DB"

echo "==> Pipeline complete!"
