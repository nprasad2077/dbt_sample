{{
    config(
        materialized='table',
        schema='intermediate',
        tags=["intermediate"]
    )
}}

WITH games AS (
    SELECT
        g.*,
        home_map.team_abbr AS home_team_abbr,
        visitor_map.team_abbr AS visitor_team_abbr,
        winning_map.team_abbr AS winning_team_abbr
    FROM {{ ref('stg_games') }} AS g
    LEFT JOIN {{ ref('team_maps') }} AS home_map ON g.home_team = home_map.full_name
    LEFT JOIN {{ ref('team_maps') }} AS visitor_map ON g.visitor_team = visitor_map.full_name
    LEFT JOIN {{ ref('team_maps') }} AS winning_map ON g.winning_team = winning_map.full_name
    WHERE (g.season_start_year >= home_map.start_year AND g.season_start_year < home_map.end_year)
    AND (g.season_start_year >= visitor_map.start_year AND g.season_start_year < visitor_map.end_year)
    AND (g.season_start_year >= winning_map.start_year AND g.season_start_year < winning_map.end_year)
),

arena_locations AS (
    SELECT arena_name, arena_city
    FROM (
        SELECT
            arena_name,
            city AS arena_city,
            ROW_NUMBER() OVER (PARTITION BY arena_name ORDER BY city) as rn
        FROM {{ ref('arena_maps') }}
    ) AS sub
    WHERE rn = 1
),

team_performance AS (
    SELECT * FROM {{ ref('int_team_performance') }}
),

final AS (
    SELECT
        g.game_id,
        g.game_date,
        g.season_start_year,
        g.is_playoff,
        g.arena,
        al.arena_city,
        g.home_team_abbr AS home_team,
        g.visitor_team_abbr AS visitor_team,
        g.winning_team_abbr AS winning_team,
        g.home_points,
        g.visitor_points,
        g.point_differential,
        g.total_points,
        g.is_overtime,
        home_stats.offensive_rating AS home_offensive_rating,
        home_stats.defensive_rating AS home_defensive_rating,
        home_stats.net_rating AS home_net_rating,
        home_stats.pace AS home_pace,
        home_stats.effective_fg_pct AS home_effective_fg_pct,
        home_stats.turnover_rate AS home_turnover_rate,
        home_stats.offensive_tier AS home_offensive_tier,
        home_stats.defensive_tier AS home_defensive_tier,
        visitor_stats.offensive_rating AS visitor_offensive_rating,
        visitor_stats.defensive_rating AS visitor_defensive_rating,
        visitor_stats.net_rating AS visitor_net_rating,
        visitor_stats.pace AS visitor_pace,
        visitor_stats.effective_fg_pct AS visitor_effective_fg_pct,
        visitor_stats.turnover_rate AS visitor_turnover_rate,
        visitor_stats.offensive_tier AS visitor_offensive_tier,
        visitor_stats.defensive_tier AS visitor_defensive_tier,
        (home_stats.pace + visitor_stats.pace) / 2 AS matchup_pace
    FROM games g
    LEFT JOIN arena_locations al ON g.arena = al.arena_name
    LEFT JOIN team_performance AS home_stats
        ON g.game_id = home_stats.game_id AND g.home_team_abbr = home_stats.team
    LEFT JOIN team_performance AS visitor_stats
        ON g.game_id = visitor_stats.game_id AND g.visitor_team_abbr = visitor_stats.team
)

SELECT * FROM final
