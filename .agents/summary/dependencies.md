# Dependencies

## dbt Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `dbt-labs/dbt_utils` | 1.3.1 | Surrogate key generation (`generate_surrogate_key`), composite uniqueness tests (`unique_combination_of_columns`) |

## Python Dependencies (Streamlit App)

| Package | Version | Purpose |
|---------|---------|---------|
| `streamlit` | 1.45.1 | Web dashboard framework |
| `duckdb` | 1.3.0 | Database connectivity (read-only) |
| `plotly` | 6.1.2 | Interactive chart visualizations |

## Evidence BI Dependencies

Managed via `reports/package.json`. Key packages:
- `@evidence-dev/evidence` — Core Evidence framework
- `@evidence-dev/duckdb` — DuckDB datasource plugin
- Additional datasource plugins installed but unused (bigquery, postgres, snowflake, etc.)

## Infrastructure Dependencies

| Dependency | Purpose | Configuration |
|-----------|---------|---------------|
| Python 3.11+ | Runtime for dbt and Streamlit | `.devcontainer/devcontainer.json` |
| Node.js | Evidence BI runtime | `reports/package.json` |
| DuckDB database file | Source data store | `data/DB/dbt_nba.duckdb` |

## Internal Model Dependencies

### Staging → Source

All staging models depend on `raw_nba` source tables (defined in `schema.yml`).

### Intermediate → Staging + Seeds

| Intermediate Model | Staging Dependencies | Seed Dependencies |
|-------------------|---------------------|-------------------|
| `int_player_performance` | `stg_player_game_basic_stats`, `stg_player_game_adv_stats_extended`, `stg_games` | `team_maps` |
| `int_team_performance` | `stg_team_game_basic_stats`, `stg_team_game_adv_stats`, `stg_games` | `team_maps` |
| `int_games_enriched` | `stg_games` | `team_maps`, `arena_maps` |
| `int_player_shots_enriched` | `stg_player_shot_charts`, `stg_player_game_basic_stats` | — |

### Marts → Intermediate + Dimensions

All fact tables reference dimension tables for surrogate key lookups. Key dependencies:

| Fact Model | Intermediate Source | Dimension Lookups |
|-----------|--------------------|--------------------|
| `fct_game_results` | `int_games_enriched` | dim_dates, dim_seasons, dim_arenas, dim_teams |
| `fct_player_game_stats` | `int_player_performance`, `int_games_enriched` | dim_players, dim_teams, dim_dates, dim_seasons, dim_arenas, dim_player_game_archetypes |
| `fct_player_game_shooting` | `int_player_shots_enriched` | dim_players, dim_teams, dim_dates, dim_seasons |
| `fct_team_game_stats` | `int_team_performance` | dim_teams, dim_dates, dim_seasons |
| `fct_quarter_scoring` | `stg_line_scores` | dim_dates, dim_seasons, dim_teams |
| `fct_player_shots` | `int_player_shots_enriched` | dim_players, dim_teams, dim_shot_zones |

## DevContainer Configuration

The `.devcontainer/devcontainer.json` configures:
- Python 3.11 base image
- Auto-installs packages from `requirements.txt`
- Auto-starts Streamlit on port 8501
- VS Code extensions: Python, Pylance
