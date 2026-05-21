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

- Python 3.11+
- dbt-duckdb adapter (included in venv)

## Setup

```bash
# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dbt packages
cd dbt_nba
dbt deps --profiles-dir .

# Load seed data (team/arena mappings)
dbt seed --profiles-dir .

# Run full build (models + tests)
dbt build --profiles-dir .
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

## Useful Commands

```bash
# Run only staging layer
dbt build --profiles-dir . --select "tag:staging"

# Run the named pipeline selector (staging → intermediate → marts)
dbt build --profiles-dir . --selector nba_pipeline

# Run tests only
dbt test --profiles-dir .

# Generate docs
dbt docs generate --profiles-dir .
dbt docs serve --profiles-dir .
```
