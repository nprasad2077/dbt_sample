# Architecture

## System Overview

dbt_nba implements a three-layer medallion architecture (staging → intermediate → marts) producing a star schema consumed by two reporting frontends.

```mermaid
graph LR
    subgraph Source
        DuckDB[(DuckDB<br/>raw tables)]
    end

    subgraph dbt Pipeline
        STG[Staging<br/>10 views]
        INT[Intermediate<br/>4 tables]
        MARTS[Marts<br/>13 tables]
    end

    subgraph Reporting
        EV[Evidence BI]
        ST[Streamlit App]
    end

    DuckDB --> STG --> INT --> MARTS
    MARTS --> EV
    MARTS --> ST
```

## Layer Architecture

```mermaid
graph TB
    subgraph Staging ["Staging Layer (views)"]
        stg_games
        stg_line_scores
        stg_player_basic[stg_player_game_basic_stats]
        stg_player_adv[stg_player_game_adv_stats]
        stg_player_adv_ext[stg_player_game_adv_stats_extended]
        stg_team_basic[stg_team_game_basic_stats]
        stg_team_adv[stg_team_game_adv_stats]
        stg_shots[stg_player_shot_charts]
        stg_season[stg_season_thresholds]
        stg_team_season[stg_team_season_thresholds]
    end

    subgraph Intermediate ["Intermediate Layer (tables)"]
        int_games[int_games_enriched]
        int_player[int_player_performance]
        int_team[int_team_performance]
        int_shots[int_player_shots_enriched]
    end

    subgraph Marts ["Marts Layer"]
        subgraph Dimensions
            dim_teams
            dim_players
            dim_seasons
            dim_dates
            dim_arenas
            dim_shot_zones
            dim_archetypes[dim_player_game_archetypes]
        end
        subgraph Facts
            fct_game[fct_game_results]
            fct_team[fct_team_game_stats]
            fct_player[fct_player_game_stats]
            fct_quarter[fct_quarter_scoring]
            fct_shots[fct_player_shots]
            fct_shooting[fct_player_game_shooting]
        end
    end

    stg_games --> int_games
    stg_team_basic --> int_team
    stg_team_adv --> int_team
    stg_player_basic --> int_player
    stg_player_adv_ext --> int_player
    stg_shots --> int_shots
    stg_player_basic --> int_shots
    int_team --> int_games

    int_games --> fct_game
    int_team --> fct_team[fct_team_game_stats]
    int_player --> fct_player
    int_player --> dim_archetypes
    int_shots --> fct_shooting
    int_shots --> fct_shots
    stg_line_scores --> fct_quarter
```

## Design Patterns

### Materialization Strategy

| Layer | Materialization | Rationale |
|-------|----------------|-----------|
| Staging | `view` | Lightweight; always reflects current source data |
| Intermediate | `table` | Expensive joins computed once; reused by multiple marts |
| Dimensions | `table` | Slowly changing; full rebuild on each run |
| Facts | `incremental` | Large tables; 30-day lookback window for efficiency |

### Incremental Strategy

All fact tables use a 30-day lookback window:
```sql
WHERE game_date >= (SELECT MAX(game_date) FROM {{ this }}) - INTERVAL '30 days'
```

### Team Abbreviation Conforming

Team names change over time (relocations, rebrands). The `team_maps` seed provides temporal validity (`start_year`, `end_year`) to correctly map team abbreviations to full names across seasons. All intermediate models join on both team abbreviation and season year range.

### Surrogate Keys

All mart tables use `dbt_utils.generate_surrogate_key()` to create deterministic surrogate keys from natural keys, enabling idempotent incremental loads.

### Star Schema Design

Fact tables reference dimension tables via surrogate keys (`team_key`, `player_key`, `date_key`, `season_key`, `arena_key`, `shot_zone_key`, `archetype_key`), enabling efficient analytical queries with dimension filtering.

## Reporting Architecture

### Evidence BI

- Node.js-based BI tool reading from a local DuckDB copy at `reports/sources/nba/dbt_nba.duckdb`
- 12 SQL query files in `reports/sources/nba/` powering dashboard visualizations
- Single-page dashboard (`reports/pages/index.md`) with embedded SQL queries

### Streamlit Dashboard

- Python app at `streamlit_app/app.py` with 7 navigation pages
- Connects read-only to the same DuckDB database
- Uses Plotly for interactive visualizations
- Queries the marts schema directly (`main_marts.*`, `main_intermediate.*`)
