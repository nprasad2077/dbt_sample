# Components

## Staging Models

Staging models clean raw source data, apply data quality filters, and derive basic metrics. All materialized as views in the `staging` schema.

| Model | Source | Responsibility |
|-------|--------|---------------|
| `stg_games` | `raw_nba.games` | Cleans game data; derives season year, time slots, winner/loser, point differential; joins overtime detection from line_scores |
| `stg_line_scores` | `raw_nba.line_scores` | Quarter-by-quarter scoring with momentum metrics |
| `stg_player_game_basic_stats` | `raw_nba.player_game_basic_stats` | Player box scores; calculates double-double/triple-double flags; filters `did_play = TRUE` |
| `stg_player_game_adv_stats` | `raw_nba.player_game_adv_stats` | Advanced player metrics with performance tiers |
| `stg_player_game_adv_stats_extended` | `raw_nba.player_game_adv_stats` | Dynamic per-season tiering using season thresholds |
| `stg_team_game_basic_stats` | `raw_nba.team_game_basic_stats` | Team box scores; calculates four factors (eFG%, TOV%, ORB%, FT rate) |
| `stg_team_game_adv_stats` | `raw_nba.team_game_adv_stats` | Team advanced stats with play style indicators |
| `stg_player_shot_charts` | `raw_nba.player_shot_charts` | Shot location data with distance zones and clutch classification |
| `stg_season_thresholds` | Derived | Per-season statistical thresholds for player tiering |
| `stg_team_season_thresholds` | Derived | Per-season statistical thresholds for team tiering |

## Intermediate Models

Intermediate models join across entities, conform team abbreviations via seed mappings, and produce enriched datasets. All materialized as tables in the `intermediate` schema.

| Model | Grain | Responsibility |
|-------|-------|---------------|
| `int_player_performance` | player × game | Joins basic + extended advanced stats; conforms team abbreviations; adds game context (result, location) |
| `int_team_performance` | team × game | Joins basic + advanced team stats; conforms abbreviations; adds opponent and game result |
| `int_games_enriched` | game | Enriches games with team performance ratings, arena locations, and conformed team abbreviations |
| `int_player_shots_enriched` | shot attempt | Unifies field goal attempts (shot charts) with free throw attempts (box scores) into single shot-level dataset |

## Mart Dimensions

Dimension tables provide descriptive attributes for analytical slicing. All materialized as tables in the `marts` schema.

| Model | Key | Description |
|-------|-----|-------------|
| `dim_teams` | `team_key` | Team abbreviation ↔ full name mapping |
| `dim_players` | `player_key` | Player identity (player_id, name) |
| `dim_seasons` | `season_key` | Season start year and metadata |
| `dim_dates` | `date_key` | Calendar date attributes |
| `dim_arenas` | `arena_key` | Arena name and city |
| `dim_shot_zones` | `shot_zone_key` | Shot distance zones with categories (7 zones from rim to free throw) |
| `dim_player_game_archetypes` | `archetype_key` | Combinatorial player archetypes from usage/impact/efficiency tiers and role flags |

## Mart Facts

Fact tables store measurable events at specific grains. All materialized as incremental tables in the `marts` schema.

| Model | Grain | Key Metrics |
|-------|-------|-------------|
| `fct_game_results` | game | Points, differential, competitiveness tier, overtime flag, net ratings |
| `fct_team_game_stats` | team × game | Offensive/defensive ratings, pace, four factors, play style |
| `fct_player_game_stats` | player × game | Points, assists, rebounds, advanced metrics, archetype reference |
| `fct_quarter_scoring` | game × quarter | Quarter-level scoring breakdown |
| `fct_player_shots` | shot attempt | Individual shot outcomes with zone and clutch context |
| `fct_player_game_shooting` | player × game | Aggregated shooting splits (FG/3P/FT/rim/clutch), shot profile type |

## Seeds

| Seed | Purpose |
|------|---------|
| `team_maps.csv` | Team abbreviation ↔ full name with temporal validity (start_year, end_year) |
| `arena_maps.csv` | Arena name → city mapping |
| `arena_mappings.csv` | Extended arena reference data |
| `team_mappings.csv` | Additional team reference data |
| `team_abbreviation_mappings.csv` | Historical abbreviation changes |

## Reporting Components

### Evidence BI (`dbt_nba/reports/`)

12 SQL query sources powering a single-page dashboard:
- `games.sql` — Game-level aggregations
- `season_summary.sql` — Season-level summaries
- `team_ratings.sql` — Team offensive/defensive ratings
- `top_scorers.sql` — Leading scorers
- `player_impact.sql` — Player impact metrics
- `usage_efficiency.sql` — Usage vs efficiency analysis
- `play_styles.sql` — Team play style breakdown
- `pace_and_scoring.sql` — Pace and scoring trends
- `home_advantage.sql` — Home court advantage analysis
- `game_drama.sql` — Close/dramatic game analysis
- `competitiveness.sql` — Game competitiveness distribution
- `home_advantage.sql` — Home/away performance splits

### Streamlit App (`streamlit_app/app.py`)

Multi-page dashboard with 7 views:
1. **Overview** — Summary metrics, competitiveness distribution, monthly game counts
2. **Teams** — Team performance comparison, ratings, win/loss records
3. **Players** — Player stats, efficiency metrics, performance tiers
4. **Shot Charts** — Shot location visualization, zone analysis
5. **Head to Head** — Team matchup comparisons
6. **Game Trends** — Scoring trends over time, pace evolution
7. **Quarter Analysis** — Quarter-by-quarter scoring patterns
