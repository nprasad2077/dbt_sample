{{
    config(
        materialized='table',
        schema='intermediate',
        tags=["intermediate"]
    )
}}

WITH basic_stats AS (
    SELECT
        s.*,
        map.team_abbr AS team_conformed
    FROM {{ ref('stg_player_game_basic_stats') }} AS s
    LEFT JOIN {{ ref('team_maps') }} AS map
        ON s.team = map.team_abbr
    LEFT JOIN {{ ref('stg_games') }} AS g
        ON s.game_id = g.game_id
    WHERE did_play = TRUE
    AND (g.season_start_year >= map.start_year AND g.season_start_year < map.end_year)
),

adv_stats AS (
    SELECT
        s.*,
        map.team_abbr AS team_conformed
    FROM {{ ref('stg_player_game_adv_stats_extended') }} AS s
    LEFT JOIN {{ ref('team_maps') }} AS map
        ON s.team = map.team_abbr
    LEFT JOIN {{ ref('stg_games') }} AS g
        ON s.game_id = g.game_id
    WHERE (g.season_start_year >= map.start_year AND g.season_start_year < map.end_year)
),

games AS (
    SELECT
        g.game_id,
        g.game_date,
        g.season_start_year,
        g.is_playoff,
        home_map.team_abbr AS home_team_abbr,
        winning_map.team_abbr AS winning_team_abbr
    FROM {{ ref('stg_games') }} g
    LEFT JOIN {{ ref('team_maps') }} AS home_map ON g.home_team = home_map.full_name
    LEFT JOIN {{ ref('team_maps') }} AS winning_map ON g.winning_team = winning_map.full_name
    WHERE (g.season_start_year >= home_map.start_year AND g.season_start_year < home_map.end_year)
    AND (g.season_start_year >= winning_map.start_year AND g.season_start_year < winning_map.end_year)
),

final AS (
    SELECT
        b.game_id,
        b.player_id,
        b.player_name,
        b.team_conformed AS team,
        g.game_date,
        g.season_start_year,
        g.is_playoff,
        CASE WHEN b.team_conformed = g.winning_team_abbr THEN 'W' ELSE 'L' END AS game_result,
        CASE WHEN b.team_conformed = g.home_team_abbr THEN 'HOME' ELSE 'AWAY' END AS team_location,
        b.minutes_played,
        b.points,
        b.assists,
        b.total_rebounds,
        b.steals,
        b.blocks,
        b.turnovers,
        b.plus_minus,
        a.net_rating,
        a.box_plus_minus,
        b.field_goals_made,
        b.field_goals_attempted,
        b.field_goal_pct,
        b.three_pointers_made,
        b.three_pointers_attempted,
        b.three_point_pct,
        a.true_shooting_pct,
        a.effective_fg_pct,
        a.usage_pct,
        a.offensive_rating,
        a.defensive_rating,
        a.usage_tier,
        a.impact_tier,
        a.shooting_efficiency_tier,
        a.minutes_based_role,
        b.is_double_double,
        b.is_triple_double,
        a.is_versatile,
        a.is_defensive_specialist,
        a.is_three_and_d
    FROM basic_stats AS b
    LEFT JOIN adv_stats AS a
        ON b.game_id = a.game_id AND b.player_id = a.player_id
    LEFT JOIN games AS g
        ON b.game_id = g.game_id
)

SELECT * FROM final
