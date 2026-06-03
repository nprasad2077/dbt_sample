# AGENTS.md

> NBA analytics data warehouse: dbt + DuckDB → star schema → Evidence BI + Streamlit dashboards.

## Directory Map

```
dbt_sample/
├── dbt_nba/                    # dbt project (all transformation logic)
│   ├── models/staging/         # 10 views — clean raw data, derive metrics
│   ├── models/intermediate/    # 4 tables — join/enrich across entities
│   ├── models/marts/dimensions/# 7 tables — descriptive attributes
│   ├── models/marts/facts/     # 6 incremental — measurable events
│   ├── seeds/                  # CSV reference data (team/arena mappings)
│   ├── reports/                # Evidence BI dashboard (Node.js)
│   └── *.yml                   # Config: dbt_project, profiles, selectors, packages
├── streamlit_app/              # Python dashboard (7 pages, Plotly charts)
├── scripts/                    # ETL: pipeline.sh + extract.sql
├── data/DB/dbt_nba.duckdb      # Source database (Git LFS)
├── pyproject.toml              # Python deps (uv package manager)
├── .github/workflows/          # Daily CI/CD pipeline
└── .devcontainer/              # Codespaces config (Python 3.11)
```

## Architecture

Three-layer medallion pipeline with Postgres extraction producing a star schema:

```mermaid
graph LR
    PG[(Postgres)] --> EXT[extract.sql] --> DuckDB[(DuckDB)]
    DuckDB --> STG[Staging<br/>views] --> INT[Intermediate<br/>tables] --> MARTS[Marts<br/>dim + fact]
    MARTS --> EV[Evidence BI]
    MARTS --> ST[Streamlit]
```

**Materializations**: staging=view, intermediate=table, dimensions=table, facts=incremental (30-day lookback).

## Key Patterns

### Team Abbreviation Conforming
Team names change over time. `seeds/team_maps.csv` has `start_year`/`end_year` columns. All intermediate models join on abbreviation AND season year range:
```sql
LEFT JOIN team_maps ON team = team_abbr
WHERE season_start_year >= start_year AND season_start_year < end_year
```

### Incremental Facts
All 6 fact tables use surrogate keys (`dbt_utils.generate_surrogate_key`) and a 30-day lookback window for idempotent refreshes.

### Shot Data Unification
`int_player_shots_enriched` combines field goal attempts (from shot charts) with free throw attempts (derived from box scores) into a single shot-level dataset with `shot_source` discriminator (`shot_chart` / `box_score_ft`).

### Dynamic Tiering
`stg_season_thresholds` computes per-season percentile breakpoints. `stg_player_game_adv_stats_extended` uses these to assign dynamic usage/impact/efficiency tiers that adjust per season.

## Model Inventory

| Layer | Models |
|-------|--------|
| Staging | stg_games, stg_line_scores, stg_player_game_basic_stats, stg_player_game_adv_stats, stg_player_game_adv_stats_extended, stg_team_game_basic_stats, stg_team_game_adv_stats, stg_player_shot_charts, stg_season_thresholds, stg_team_season_thresholds |
| Intermediate | int_games_enriched, int_player_performance, int_team_performance, int_player_shots_enriched |
| Dimensions | dim_teams, dim_players, dim_seasons, dim_dates, dim_arenas, dim_shot_zones, dim_player_game_archetypes |
| Facts | fct_game_results, fct_team_game_stats, fct_player_game_stats, fct_quarter_scoring, fct_player_shots, fct_player_game_shooting |

## Configuration

Key variables in `dbt_project.yml`:
- `start_date` / `end_date` — date range filter
- `min_games_played` (10), `min_minutes_per_game` (15) — player inclusion thresholds
- `clutch_time_minutes` (5), `close_game_margin` (5) — clutch game definitions

## Pipeline Execution

All dbt commands run from `dbt_nba/` directory via uv:
- Full build: `uv run --project .. dbt build --profiles-dir .`
- By layer: `uv run --project .. dbt build --profiles-dir . --select "tag:staging"`
- Named selector: `uv run --project .. dbt build --profiles-dir . --selector nba_pipeline`
- Seeds: `uv run --project .. dbt seed --profiles-dir .`
- Full ETL: `./scripts/pipeline.sh` (requires `POSTGRES_URL` env var)

## CI/CD

GitHub Actions (`.github/workflows/pipeline.yml`):
- **Schedule**: Daily at 06:00 UTC + manual dispatch
- **Steps**: Checkout (LFS) → setup uv + DuckDB CLI → `./scripts/pipeline.sh` → commit updated .duckdb files
- **Secret**: `POSTGRES_URL` (Postgres connection string)

## Reporting

- **Evidence BI** (`dbt_nba/reports/`): 12 SQL queries in `sources/nba/`, single dashboard page. Reads local DuckDB copy.
- **Streamlit** (`streamlit_app/app.py`): 7 pages (Overview, Teams, Players, Shot Charts, Head to Head, Game Trends, Quarter Analysis). Queries `main_marts.*` and `main_intermediate.*` schemas from reports DuckDB copy.

## Dependencies

- `dbt-labs/dbt_utils` 1.3.1 — surrogate keys, unpivot, composite uniqueness tests
- Python (via `pyproject.toml` + uv): dbt-duckdb, streamlit >=1.45.1, duckdb >=1.3.0, plotly >=6.1.2
- DuckDB Postgres extension — source extraction

## Known Gaps

- No schema YAML for marts layer (dimensions/facts have no tests)
- `team_mappings.csv` and `team_abbreviation_mappings.csv` usage by models is unclear
- Pipeline has no failure alerting or retry logic

## Detailed Documentation

For deeper information, see `.agents/summary/index.md` which maps to:
- `architecture.md` — design decisions, extraction architecture, layer patterns
- `components.md` — model-by-model responsibilities
- `data_models.md` — column-level schema details, ER diagrams
- `interfaces.md` — connection paths, source contracts, query interfaces
- `workflows.md` — pipeline execution, CI/CD, transformation flows, dev workflow
- `dependencies.md` — full dependency graph (Mermaid DAG)

## Custom Instructions
<!-- This section is for human and agent-maintained operational knowledge.
     Add repo-specific conventions, gotchas, and workflow rules here.
     This section is preserved exactly as-is when re-running codebase-summary. -->

