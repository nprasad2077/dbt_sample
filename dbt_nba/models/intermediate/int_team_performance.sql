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
    FROM {{ ref('stg_team_game_basic_stats') }} AS s
    LEFT JOIN {{ ref('team_maps') }} AS map
        ON s.team = map.team_abbr
    LEFT JOIN {{ ref('stg_games') }} AS g
        ON s.game_id = g.game_id
    WHERE (g.season_start_year >= map.start_year AND g.season_start_year < map.end_year)
),

adv_stats AS (
    SELECT
        s.*,
        map.team_abbr AS team_conformed
    FROM {{ ref('stg_team_game_adv_stats') }} AS s
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
        visitor_map.team_abbr AS visitor_team_abbr,
        winning_map.team_abbr AS winning_team_abbr
    FROM {{ ref('stg_games') }} g
    LEFT JOIN {{ ref('team_maps') }} AS home_map ON g.home_team = home_map.full_name
    LEFT JOIN {{ ref('team_maps') }} AS visitor_map ON g.visitor_team = visitor_map.full_name
    LEFT JOIN {{ ref('team_maps') }} AS winning_map ON g.winning_team = winning_map.full_name
    WHERE (g.season_start_year >= home_map.start_year AND g.season_start_year < home_map.end_year)
    AND (g.season_start_year >= visitor_map.start_year AND g.season_start_year < visitor_map.end_year)
    AND (g.season_start_year >= winning_map.start_year AND g.season_start_year < winning_map.end_year)
),

final AS (
    SELECT
        b.game_id,
        b.team_conformed AS team,
        g.game_date,
        g.season_start_year,
        g.is_playoff,
        CASE WHEN b.team_conformed = g.winning_team_abbr THEN 'W' ELSE 'L' END AS game_result,
        CASE
            WHEN b.team_conformed = g.home_team_abbr THEN g.visitor_team_abbr
            ELSE g.home_team_abbr
        END AS opponent_team,
        b.points,
        a.offensive_rating,
        a.defensive_rating,
        a.net_rating,
        b.pace,
        b.effective_fg_pct,
        b.turnover_rate,
        b.offensive_rebound_rate,
        b.free_throw_rate,
        a.offensive_tier,
        a.defensive_tier,
        a.shot_selection_style,
        a.ball_movement_style,
        a.ball_security_tier,
        a.defensive_activity
    FROM basic_stats AS b
    LEFT JOIN adv_stats AS a
        ON b.game_id = a.game_id AND b.team_conformed = a.team_conformed
    LEFT JOIN games AS g
        ON b.game_id = g.game_id
)

SELECT * FROM final
