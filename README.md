# dbt_nba

NBA analytics data warehouse built with dbt and DuckDB. Transforms raw basketball data (games, player stats, team stats, shot charts) into a dimensional model for analysis.

## Architecture

```
Source (DuckDB)          Staging              Intermediate           Marts
─────────────────   ─────────────────   ─────────────────────   ─────────────────
games              → stg_games          → int_games_enriched    → fct_game_results
line_scores        → stg_line_scores    → int_team_performance  → fct_team_game_stats
player_game_basic  → stg_player_basic   → int_player_performance→ fct_player_game_stats
player_game_adv    → stg_player_adv     →                       → fct_quarter_scoring
player_shot_charts → stg_shot_charts    → int_player_shots      → fct_player_shots
team_game_basic    → stg_team_basic       enriched              → fct_player_game_shooting
team_game_adv      → stg_team_adv
                     stg_season_thresholds                        dim_teams, dim_players,
                     stg_team_season_thresholds                   dim_seasons, dim_dates,
                                                                  dim_arenas, dim_shot_zones,
                                                                  dim_player_game_archetypes
```

**Layers:**

- **Staging** — Cleans raw data, derives basic metrics, applies data quality filters
- **Intermediate** — Joins and enriches across entities, conforms team abbreviations via seed mappings
- **Marts** — Star schema with dimension and fact tables for analytics consumption

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [DuckDB CLI](https://duckdb.org/docs/installation/)
- Git LFS (`git lfs install`)

## Setup

```bash
# Clone and pull LFS-tracked database
git clone <repo-url>
cd dbt_sample
git lfs install
git lfs pull

# Install Python 3.12 (if not already available)
uv python install 3.12

# Run dbt build (uv handles venv + deps automatically)
cd dbt_nba
uv run --project .. dbt deps --profiles-dir .
uv run --project .. dbt seed --profiles-dir .
uv run --project .. dbt build --profiles-dir .
```

## Source Database

DuckDB database at `data/DB/dbt_nba.duckdb` containing:

- `games` — Game results, scores, venues
- `line_scores` — Quarter-by-quarter scoring
- `player_game_basic_stats` — Points, rebounds, assists per player per game
- `player_game_adv_stats` — Advanced metrics (BPM, usage%, ratings)
- `player_shot_charts` — Individual shot locations and outcomes
- `team_game_basic_stats` — Team box score totals
- `team_game_adv_stats` — Team advanced metrics

## Data Pipeline

The full pipeline extracts source data from Postgres, runs dbt transformations, and copies the result to the reports database.

### Prerequisites

- DuckDB CLI installed
- `POSTGRES_URL` environment variable set (e.g., `postgresql://user:pass@host:5432/dbname`)
- dbt packages installed (`dbt deps --profiles-dir .` from `dbt_nba/`)

### Run Full Pipeline

```bash
export POSTGRES_URL="postgresql://user:pass@host:5432/nba"
./scripts/pipeline.sh
```

This will:
1. Extract all 7 source tables from Postgres into `data/DB/dbt_nba.duckdb`
2. Run `dbt build` (staging → intermediate → marts + tests)
3. Copy the database to `dbt_nba/reports/sources/nba/dbt_nba.duckdb` for reporting

### Run Extraction Only

```bash
export POSTGRES_URL="postgresql://user:pass@host:5432/nba"
duckdb data/DB/dbt_nba.duckdb < scripts/extract.sql
```

## Useful Commands

```bash
# Run only staging layer
uv run --project .. dbt build --profiles-dir . --select "tag:staging"

# Run the named pipeline selector (staging → intermediate → marts)
uv run --project .. dbt build --profiles-dir . --selector nba_pipeline

# Run tests only
uv run --project .. dbt test --profiles-dir .

# Generate docs
uv run --project .. dbt docs generate --profiles-dir .
uv run --project .. dbt docs serve --profiles-dir .
```
