# Interfaces

## Data Source Interface

### DuckDB Connection

The project connects to a single DuckDB database file. Two connection paths exist:

| Consumer | Path | Mode |
|----------|------|------|
| dbt | `../data/DB/dbt_nba.duckdb` (relative to `dbt_nba/`) | Read/Write |
| Evidence BI | `reports/sources/nba/dbt_nba.duckdb` (local copy) | Read-only |
| Streamlit | `dbt_nba/reports/sources/nba/dbt_nba.duckdb` | Read-only |

### Source Schema Contract

dbt expects 7 tables in the `main` schema with the following key constraints:

```mermaid
erDiagram
    games {
        string game_id PK
        string home_team
        string visitor_team
        date date
        int home_pts
        int visitor_pts
    }
    line_scores {
        string game_id FK
        int quarter
        int overtime_points
    }
    player_game_basic_stats {
        string game_id FK
        string player_id FK
        string team
        float minutes_played
    }
    player_game_adv_stats {
        string game_id FK
        string player_id FK
        float usage_pct
        float net_rating
    }
    player_shot_charts {
        string id PK
        string player_id FK
        string game_id FK
        int distance_ft
        bool shot_made_flag
    }
    team_game_basic_stats {
        string game_id FK
        string team FK
        int points
        float pace
    }
    team_game_adv_stats {
        string game_id FK
        string team FK
        float offensive_rating
        float defensive_rating
    }

    games ||--o{ line_scores : "game_id"
    games ||--o{ player_game_basic_stats : "game_id"
    games ||--o{ player_game_adv_stats : "game_id"
    games ||--o{ player_shot_charts : "game_id"
    games ||--o{ team_game_basic_stats : "game_id"
    games ||--o{ team_game_adv_stats : "game_id"
```

## dbt Model Interface

### Seed Dependencies

Intermediate models depend on seeds for team/arena conforming:

| Seed | Used By | Join Pattern |
|------|---------|-------------|
| `team_maps` | `int_games_enriched`, `int_player_performance`, `int_team_performance` | `ON team = team_abbr WHERE season_start_year BETWEEN start_year AND end_year` |
| `arena_maps` | `int_games_enriched` | `ON arena = arena_name` |

### Cross-Layer References

```mermaid
graph TD
    subgraph Seeds
        team_maps
        arena_maps
    end

    subgraph Staging
        stg_games
        stg_player_basic[stg_player_game_basic_stats]
        stg_player_adv_ext[stg_player_game_adv_stats_extended]
        stg_team_basic[stg_team_game_basic_stats]
        stg_team_adv[stg_team_game_adv_stats]
        stg_shots[stg_player_shot_charts]
        stg_line_scores
    end

    subgraph Intermediate
        int_games[int_games_enriched]
        int_player[int_player_performance]
        int_team[int_team_performance]
        int_shots[int_player_shots_enriched]
    end

    team_maps --> int_games
    team_maps --> int_player
    team_maps --> int_team
    arena_maps --> int_games
    stg_games --> int_games
    int_team --> int_games
    stg_player_basic --> int_player
    stg_player_adv_ext --> int_player
    stg_team_basic --> int_team
    stg_team_adv --> int_team
    stg_shots --> int_shots
    stg_player_basic --> int_shots
    stg_line_scores --> stg_games
```

## Reporting Query Interface

### Evidence BI Queries

Evidence queries read from the marts and intermediate schemas:

| Query File | Schema | Primary Table |
|-----------|--------|---------------|
| `games.sql` | main_marts | fct_game_results |
| `season_summary.sql` | main_marts | fct_game_results |
| `team_ratings.sql` | main_intermediate | int_team_performance |
| `top_scorers.sql` | main_intermediate | int_player_performance |
| `player_impact.sql` | main_intermediate | int_player_performance |
| `usage_efficiency.sql` | main_intermediate | int_player_performance |
| `play_styles.sql` | main_intermediate | int_team_performance |
| `pace_and_scoring.sql` | main_intermediate | int_team_performance |
| `home_advantage.sql` | main_intermediate | int_games_enriched |
| `game_drama.sql` | main_marts | fct_game_results |
| `competitiveness.sql` | main_marts | fct_game_results |

### Streamlit Query Interface

The Streamlit app queries via `duckdb.connect(DB_PATH, read_only=True)` and uses:
- `main_marts.fct_game_results`
- `main_marts.fct_player_game_stats`
- `main_marts.fct_team_game_stats`
- `main_marts.fct_player_game_shooting`
- `main_intermediate.int_games_enriched`
- `main_intermediate.int_player_performance`

## Pipeline Execution Interface

### Selectors

The `nba_pipeline` selector runs the full DAG via tag union:
```yaml
definition:
  union:
    - method: tag
      value: staging
    - method: tag
      value: intermediate
    - method: tag
      value: dimension
    - method: tag
      value: fact
    - method: tag
      value: marts
```

### Tag-Based Execution

| Tag | Models | Command |
|-----|--------|---------|
| `staging` | All staging views | `dbt build --select "tag:staging"` |
| `intermediate` | All intermediate tables | `dbt build --select "tag:intermediate"` |
| `dimension` | All dimension tables | `dbt build --select "tag:dimension"` |
| `fact` | All fact tables | `dbt build --select "tag:fact"` |
| `marts` | All marts (dim + fact) | `dbt build --select "tag:marts"` |
