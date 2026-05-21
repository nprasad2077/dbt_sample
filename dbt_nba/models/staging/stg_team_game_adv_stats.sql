{{
    config(
        materialized='table',
        schema='staging',
        tags=["staging"]
    )
}}

WITH source_data AS (
    SELECT * FROM {{ source('raw_nba', 'team_game_adv_stats') }}
    WHERE deleted_at IS NULL
),

games AS (
    SELECT game_id, season_start_year
    FROM {{ ref('stg_games') }}
),

team_season_thresholds AS (
    SELECT * FROM {{ ref('stg_team_season_thresholds') }}
),

cleaned AS (
    SELECT
        sd.game_id,
        sd.team,
        COALESCE(sd.mp, 240) AS minutes_played,
        COALESCE(sd.ts_percent, 0) AS true_shooting_pct,
        COALESCE(sd.efg_percent, 0) AS effective_fg_pct,
        COALESCE(sd.three_p_ar, 0) AS three_point_attempt_rate,
        COALESCE(sd.f_tr, 0) AS free_throw_rate,
        COALESCE(sd.orb_percent, 0) AS offensive_rebound_pct,
        COALESCE(sd.drb_percent, 0) AS defensive_rebound_pct,
        COALESCE(sd.trb_percent, 0) AS total_rebound_pct,
        COALESCE(sd.ast_percent, 0) AS assist_pct,
        COALESCE(sd.stl_percent, 0) AS steal_pct,
        COALESCE(sd.blk_percent, 0) AS block_pct,
        COALESCE(sd.tov_percent, 0) AS turnover_pct,
        COALESCE(sd.usg_percent, 100) AS usage_pct,
        COALESCE(sd.o_rtg, 0) AS offensive_rating,
        COALESCE(sd.d_rtg, 0) AS defensive_rating,
        COALESCE(sd.o_rtg, 0) - COALESCE(sd.d_rtg, 0) AS net_rating,

        CASE
            WHEN COALESCE(sd.o_rtg, 0) >= t.ortg_p90 THEN 'Elite Offense'
            WHEN COALESCE(sd.o_rtg, 0) >= t.ortg_q3 THEN 'Above Average Offense'
            WHEN COALESCE(sd.o_rtg, 0) >= t.ortg_q1 THEN 'Average Offense'
            WHEN COALESCE(sd.o_rtg, 0) >= t.ortg_p10 THEN 'Below Average Offense'
            ELSE 'Poor Offense'
        END AS offensive_tier,

        CASE
            WHEN COALESCE(sd.d_rtg, 0) <= t.drtg_p10 THEN 'Elite Defense'
            WHEN COALESCE(sd.d_rtg, 0) <= t.drtg_q1 THEN 'Above Average Defense'
            WHEN COALESCE(sd.d_rtg, 0) <= t.drtg_q3 THEN 'Average Defense'
            WHEN COALESCE(sd.d_rtg, 0) <= t.drtg_p90 THEN 'Below Average Defense'
            ELSE 'Poor Defense'
        END AS defensive_tier,

        CASE
            WHEN COALESCE(sd.three_p_ar, 0) >= t.tpar_p90 THEN 'Three Point Heavy'
            WHEN COALESCE(sd.three_p_ar, 0) >= t.tpar_q3 THEN 'Three Point Leaning'
            WHEN COALESCE(sd.three_p_ar, 0) >= t.tpar_q1 THEN 'Balanced'
            WHEN COALESCE(sd.three_p_ar, 0) >= t.tpar_p10 THEN 'Inside Leaning'
            ELSE 'Inside Focused'
        END AS shot_selection_style,

        CASE
            WHEN COALESCE(sd.ast_percent, 0) >= t.ast_p90 THEN 'Elite Ball Movement'
            WHEN COALESCE(sd.ast_percent, 0) >= t.ast_q3 THEN 'High Ball Movement'
            WHEN COALESCE(sd.ast_percent, 0) >= t.ast_q1 THEN 'Average Ball Movement'
            WHEN COALESCE(sd.ast_percent, 0) >= t.ast_p10 THEN 'Low Ball Movement'
            ELSE 'Isolation Heavy'
        END AS ball_movement_style,

        CASE
            WHEN COALESCE(sd.tov_percent, 0) <= t.tov_p10 THEN 'Elite Ball Security'
            WHEN COALESCE(sd.tov_percent, 0) <= t.tov_q1 THEN 'Above Average Ball Security'
            WHEN COALESCE(sd.tov_percent, 0) <= t.tov_q3 THEN 'Average Ball Security'
            WHEN COALESCE(sd.tov_percent, 0) <= t.tov_p90 THEN 'Below Average Ball Security'
            ELSE 'Poor Ball Security'
        END AS ball_security_tier,

        CASE
            WHEN (COALESCE(sd.stl_percent, 0) + COALESCE(sd.blk_percent, 0)) >= t.stl_blk_p90 THEN 'Elite Defensive Activity'
            WHEN (COALESCE(sd.stl_percent, 0) + COALESCE(sd.blk_percent, 0)) >= t.stl_blk_q3 THEN 'High Defensive Activity'
            WHEN (COALESCE(sd.stl_percent, 0) + COALESCE(sd.blk_percent, 0)) >= t.stl_blk_q1 THEN 'Average Defensive Activity'
            WHEN (COALESCE(sd.stl_percent, 0) + COALESCE(sd.blk_percent, 0)) >= t.stl_blk_p10 THEN 'Low Defensive Activity'
            ELSE 'Passive Defense'
        END AS defensive_activity,

        sd.created_at,
        sd.updated_at,
        CURRENT_TIMESTAMP AS dbt_loaded_at

    FROM source_data AS sd
    LEFT JOIN games AS g ON sd.game_id = g.game_id
    LEFT JOIN team_season_thresholds AS t ON g.season_start_year = t.season_start_year
    WHERE sd.game_id IS NOT NULL AND sd.team IS NOT NULL
)

SELECT * FROM cleaned
