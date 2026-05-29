# Data Models

## Star Schema Overview

```mermaid
erDiagram
    dim_teams ||--o{ fct_game_results : "home/visitor/winning_team_key"
    dim_teams ||--o{ fct_team_game_stats : "team_key"
    dim_teams ||--o{ fct_player_game_stats : "team_key"
    dim_teams ||--o{ fct_player_game_shooting : "team_key, opponent_key"
    dim_players ||--o{ fct_player_game_stats : "player_key"
    dim_players ||--o{ fct_player_game_shooting : "player_key"
    dim_dates ||--o{ fct_game_results : "date_key"
    dim_dates ||--o{ fct_player_game_stats : "date_key"
    dim_dates ||--o{ fct_player_game_shooting : "date_key"
    dim_seasons ||--o{ fct_game_results : "season_key"
    dim_seasons ||--o{ fct_player_game_stats : "season_key"
    dim_arenas ||--o{ fct_game_results : "arena_key"
    dim_arenas ||--o{ fct_player_game_stats : "arena_key"
    dim_shot_zones ||--o{ fct_player_shots : "shot_zone_key"
    dim_player_game_archetypes ||--o{ fct_player_game_stats : "archetype_key"

    dim_teams {
        string team_key PK
        string team_abbr
        string team_full_name
    }
    dim_players {
        string player_key PK
        string player_id
        string player_name
    }
    dim_seasons {
        string season_key PK
        int season_start_year
    }
    dim_dates {
        string date_key PK
        date full_date
    }
    dim_arenas {
        string arena_key PK
        string arena_name
        string arena_city
    }
    dim_shot_zones {
        string shot_zone_key PK
        string shot_distance_zone
        int min_distance_ft
        int max_distance_ft
        int zone_order
        string zone_group
        string zone_category
        string shot_class
    }
    dim_player_game_archetypes {
        string archetype_key PK
        string usage_tier
        string impact_tier
        string shooting_efficiency_tier
        string minutes_based_role
        bool is_double_double
        bool is_triple_double
        bool is_versatile
        bool is_defensive_specialist
        bool is_three_and_d
    }
```

## Fact Table Details

### fct_game_results (grain: game)

| Column | Type | Description |
|--------|------|-------------|
| game_key | string | Surrogate key (from game_id) |
| date_key | string | FK → dim_dates |
| season_key | string | FK → dim_seasons |
| arena_key | string | FK → dim_arenas |
| home_team_key | string | FK → dim_teams |
| visitor_team_key | string | FK → dim_teams |
| winning_team_key | string | FK → dim_teams |
| home_points | int | Home team score |
| visitor_points | int | Visitor team score |
| point_differential | int | Absolute margin |
| total_points | int | Combined score |
| is_playoff | bool | Playoff game flag |
| is_overtime | bool | Overtime game flag |
| is_home_team_winner | bool | Home win flag |
| home_net_rating | float | Home team net rating |
| visitor_net_rating | float | Visitor team net rating |
| matchup_pace | float | Average pace of both teams |
| game_competitiveness_tier | string | Clutch/Competitive/Decisive/Blowout |

### fct_player_game_stats (grain: player × game)

| Column | Type | Description |
|--------|------|-------------|
| player_game_key | string | Surrogate key (game_id + player_id) |
| player_key | string | FK → dim_players |
| team_key | string | FK → dim_teams |
| archetype_key | string | FK → dim_player_game_archetypes |
| minutes_played | float | Minutes on court |
| points, assists, total_rebounds | int | Core box score stats |
| steals, blocks, turnovers | int | Defensive/ball handling |
| plus_minus | int | On-court point differential |
| net_rating | float | Points per 100 possessions differential |
| box_plus_minus | float | Estimated contribution |
| true_shooting_pct | float | Efficiency including FT and 3P |
| usage_pct | float | Percentage of team plays used |
| offensive_rating, defensive_rating | float | Per-100-possession ratings |

### fct_player_game_shooting (grain: player × game)

| Column | Type | Description |
|--------|------|-------------|
| player_game_shooting_key | string | Surrogate key |
| fg_attempts, fg_makes, fg_pct | numeric | Field goal totals |
| ft_attempts, ft_makes, ft_pct | numeric | Free throw totals |
| three_point_attempts/makes/fg_pct | numeric | Three-point totals |
| at_rim_attempts/makes/fg_pct | numeric | Rim finishing |
| clutch_fg_attempts/makes/fg_pct | numeric | Clutch shooting |
| three_point_rate | float | 3PA / FGA ratio |
| at_rim_rate | float | Rim attempts / FGA ratio |
| mid_range_rate | float | Mid-range / FGA ratio |
| avg_fg_distance_ft | float | Average shot distance |
| true_shooting_pct | float | Overall efficiency |
| shot_profile_type | string | Perimeter Heavy/Rim Attacker/Mid Range Heavy/Modern/Balanced |

### fct_team_game_stats (grain: team × game)

Key metrics: offensive/defensive/net rating, pace, four factors, play style indicators.

### fct_quarter_scoring (grain: game × quarter)

Quarter-level scoring breakdown for momentum analysis.

### fct_player_shots (grain: shot attempt)

Individual shot-level data with zone, distance, and outcome.

## Shot Zone Classification

| Zone | Distance | Category |
|------|----------|----------|
| At Rim (0-3 ft) | 0-3 ft | Interior |
| Short Range (4-10 ft) | 4-10 ft | Interior |
| Mid Range (11-16 ft) | 11-16 ft | Mid Range |
| Long Mid Range (17-23 ft) | 17-23 ft | Mid Range |
| Three Point (24-27 ft) | 24-27 ft | Three Point |
| Deep Three (28+ ft) | 28-50 ft | Three Point |
| Free Throw (15 ft) | 15 ft | Free Throw |

## Player Archetype Dimensions

Archetypes are combinatorial, derived from:
- **usage_tier** — Player's share of team possessions
- **impact_tier** — Overall contribution level
- **shooting_efficiency_tier** — Scoring efficiency classification
- **minutes_based_role** — Starter/rotation/bench classification
- **Boolean flags** — is_double_double, is_triple_double, is_versatile, is_defensive_specialist, is_three_and_d
