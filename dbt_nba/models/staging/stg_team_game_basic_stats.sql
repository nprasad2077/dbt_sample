{{
    config(
        materialized='view',
        schema='staging'
    )
}}

WITH source_data AS (
    SELECT * FROM {{ source('raw_nba', 'team_game_basic_stats') }}
    WHERE deleted_at IS NULL
),

cleaned AS (
    SELECT
        game_id,
        team,
        COALESCE(mp, 240) AS minutes_played,
        COALESCE(fg, 0) AS field_goals_made,
        COALESCE(fga, 0) AS field_goals_attempted,
        COALESCE(fg_percent, 0) AS field_goal_pct,
        COALESCE(three_p, 0) AS three_pointers_made,
        COALESCE(three_pa, 0) AS three_pointers_attempted,
        COALESCE(three_p_percent, 0) AS three_point_pct,
        COALESCE(ft, 0) AS free_throws_made,
        COALESCE(fta, 0) AS free_throws_attempted,
        COALESCE(ft_percent, 0) AS free_throw_pct,
        COALESCE(orb, 0) AS offensive_rebounds,
        COALESCE(drb, 0) AS defensive_rebounds,
        COALESCE(trb, 0) AS total_rebounds,
        COALESCE(ast, 0) AS assists,
        COALESCE(stl, 0) AS steals,
        COALESCE(blk, 0) AS blocks,
        COALESCE(tov, 0) AS turnovers,
        COALESCE(pf, 0) AS personal_fouls,
        COALESCE(pts, 0) AS points,
        COALESCE(fg, 0) - COALESCE(three_p, 0) AS two_pointers_made,
        COALESCE(fga, 0) - COALESCE(three_pa, 0) AS two_pointers_attempted,
        CASE
            WHEN (COALESCE(fga, 0) - COALESCE(three_pa, 0)) > 0 THEN
                CAST(COALESCE(fg, 0) - COALESCE(three_p, 0) AS DECIMAL) /
                CAST(COALESCE(fga, 0) - COALESCE(three_pa, 0) AS DECIMAL)
            ELSE 0
        END AS two_point_pct,
        COALESCE(fga, 0) + 0.44 * COALESCE(fta, 0) - COALESCE(orb, 0) + COALESCE(tov, 0) AS possessions_estimate,
        CASE
            WHEN COALESCE(mp, 240) > 0 THEN
                (COALESCE(fga, 0) + 0.44 * COALESCE(fta, 0) - COALESCE(orb, 0) + COALESCE(tov, 0)) * 48.0 / (COALESCE(mp, 240) / 5.0)
            ELSE 0
        END AS pace,
        CASE
            WHEN COALESCE(fga, 0) > 0 THEN
                CAST(COALESCE(fg, 0) + 0.5 * COALESCE(three_p, 0) AS DECIMAL) / CAST(COALESCE(fga, 0) AS DECIMAL)
            ELSE 0
        END AS effective_fg_pct,
        CASE
            WHEN (COALESCE(fga, 0) + 0.44 * COALESCE(fta, 0) + COALESCE(tov, 0)) > 0 THEN
                CAST(COALESCE(tov, 0) AS DECIMAL) / CAST(COALESCE(fga, 0) + 0.44 * COALESCE(fta, 0) + COALESCE(tov, 0) AS DECIMAL)
            ELSE 0
        END AS turnover_rate,
        CASE
            WHEN (COALESCE(orb, 0) + COALESCE(drb, 0)) > 0 THEN
                CAST(COALESCE(orb, 0) AS DECIMAL) / CAST(COALESCE(orb, 0) + COALESCE(drb, 0) AS DECIMAL)
            ELSE 0
        END AS offensive_rebound_rate,
        CASE
            WHEN COALESCE(fga, 0) > 0 THEN
                CAST(COALESCE(fta, 0) AS DECIMAL) / CAST(COALESCE(fga, 0) AS DECIMAL)
            ELSE 0
        END AS free_throw_rate,
        CASE
            WHEN COALESCE(tov, 0) > 0 THEN
                CAST(COALESCE(ast, 0) AS DECIMAL) / CAST(COALESCE(tov, 0) AS DECIMAL)
            ELSE 0
        END AS ast_to_tov_ratio,
        CASE
            WHEN (COALESCE(fga, 0) + 0.44 * COALESCE(fta, 0) - COALESCE(orb, 0) + COALESCE(tov, 0)) > 0 THEN
                CAST(COALESCE(pts, 0) AS DECIMAL) / CAST(COALESCE(fga, 0) + 0.44 * COALESCE(fta, 0) - COALESCE(orb, 0) + COALESCE(tov, 0) AS DECIMAL)
            ELSE 0
        END AS points_per_possession,
        CASE
            WHEN COALESCE(fga, 0) > 0 THEN
                CAST(COALESCE(three_pa, 0) AS DECIMAL) / CAST(COALESCE(fga, 0) AS DECIMAL)
            ELSE 0
        END AS three_point_rate,
        created_at,
        updated_at,
        CURRENT_TIMESTAMP AS dbt_loaded_at
    FROM source_data
    WHERE game_id IS NOT NULL AND team IS NOT NULL
)

SELECT * FROM cleaned
