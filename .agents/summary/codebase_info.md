# Codebase Information

## Project Identity

- **Name**: dbt_nba
- **Purpose**: NBA analytics data warehouse transforming raw basketball data into a dimensional model for analysis
- **Primary Language**: SQL (dbt/Jinja)
- **Secondary Language**: Python (Streamlit dashboard)
- **Framework**: dbt (data build tool) with DuckDB adapter
- **License**: GPL (see LICENSE)

## Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Transformation | dbt-core | — |
| Database | DuckDB | 1.3.0 |
| dbt Adapter | dbt-duckdb | — |
| dbt Package | dbt_utils | 1.3.1 |
| BI Reporting | Evidence | (Node.js) |
| Dashboard | Streamlit | 1.45.1 |
| Visualization | Plotly | 6.1.2 |
| Runtime | Python | 3.11+ |

## Repository Structure

```
dbt_sample/
├── dbt_nba/                    # dbt project root
│   ├── models/
│   │   ├── staging/            # 10 view models (raw → cleaned)
│   │   ├── intermediate/       # 4 table models (enriched joins)
│   │   └── marts/
│   │       ├── dimensions/     # 7 dimension tables
│   │       └── facts/          # 6 incremental fact tables
│   ├── seeds/                  # CSV reference data (team/arena mappings)
│   ├── reports/                # Evidence BI project
│   │   ├── pages/              # Evidence markdown pages
│   │   └── sources/nba/        # SQL queries + DuckDB connection
│   ├── dbt_project.yml         # Project configuration
│   ├── profiles.yml            # DuckDB connection profile
│   ├── selectors.yml           # Pipeline selector definitions
│   └── packages.yml            # dbt package dependencies
├── streamlit_app/              # Interactive Python dashboard
│   ├── app.py                  # Multi-page Streamlit application
│   ├── requirements.txt        # Python dependencies
│   └── .streamlit/config.toml  # Streamlit server config
├── data/DB/dbt_nba.duckdb      # Source DuckDB database
├── .devcontainer/              # Codespaces/DevContainer config
└── README.md                   # Project documentation
```

## Configuration Variables (dbt_project.yml)

| Variable | Default | Purpose |
|----------|---------|---------|
| `start_date` | 2002-10-01 | Earliest game date to process |
| `end_date` | 2025-11-10 | Latest game date to process |
| `min_games_played` | 10 | Minimum games for player inclusion |
| `min_minutes_per_game` | 15 | Minimum minutes for player inclusion |
| `clutch_time_minutes` | 5 | Minutes remaining for clutch classification |
| `close_game_margin` | 5 | Point margin for close game classification |

## Source Data (7 tables in DuckDB `main` schema)

| Source Table | Description | Key Columns |
|-------------|-------------|-------------|
| `games` | Game results, scores, venues | game_id (PK) |
| `line_scores` | Quarter-by-quarter scoring | game_id |
| `player_game_basic_stats` | Points, rebounds, assists per player | game_id, player_id |
| `player_game_adv_stats` | BPM, usage%, ratings per player | game_id, player_id |
| `player_shot_charts` | Individual shot locations/outcomes | id (PK) |
| `team_game_basic_stats` | Team box score totals | game_id, team |
| `team_game_adv_stats` | Team advanced metrics | game_id, team |
