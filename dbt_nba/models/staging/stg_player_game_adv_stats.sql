{{
    config(
        materialized='view',
        schema='staging'
    )
}}

WITH source_data AS (
    SELECT * FROM {{ source('raw_nba', 'player_game_adv_stats') }}
    WHERE deleted_at IS NULL
),

with_minutes AS (
    SELECT
        *,
        CASE
            WHEN mp IS NOT NULL AND mp != '' AND mp LIKE '%:%' THEN
                CAST(SPLIT_PART(mp, ':', 1) AS DECIMAL) +
                (CAST(SPLIT_PART(mp, ':', 2) AS DECIMAL) / 60.0)
            WHEN mp IS NOT NULL AND mp != '' THEN CAST(mp AS DECIMAL)
            ELSE 0
        END AS minutes_played_calc
    FROM source_data
),

cleaned AS (
    SELECT
        game_id,
        player_id,
        team,
        player_name,
        mp AS minutes_played_str,
        minutes_played_calc AS minutes_played,
        COALESCE(ts_percent, 0) AS true_shooting_pct,
        COALESCE(efg_percent, 0) AS effective_fg_pct,
        COALESCE(three_p_ar, 0) AS three_point_attempt_rate,
        COALESCE(f_tr, 0) AS free_throw_rate,
        COALESCE(orb_percent, 0) AS offensive_rebound_pct,
        COALESCE(drb_percent, 0) AS defensive_rebound_pct,
        COALESCE(trb_percent, 0) AS total_rebound_pct,
        COALESCE(ast_percent, 0) AS assist_pct,
        COALESCE(stl_percent, 0) AS steal_pct,
        COALESCE(blk_percent, 0) AS block_pct,
        COALESCE(tov_percent, 0) AS turnover_pct,
        COALESCE(usg_percent, 0) AS usage_pct,
        COALESCE(o_rtg, 0) AS offensive_rating,
        COALESCE(d_rtg, 0) AS defensive_rating,
        COALESCE(bpm, 0) AS box_plus_minus,
        COALESCE(o_rtg, 0) - COALESCE(d_rtg, 0) AS net_rating,
        CASE
            WHEN minutes_played_calc < 5 THEN 'Insufficient Minutes'
            WHEN COALESCE(ts_percent, 0) >= 0.60 THEN 'Elite'
            WHEN COALESCE(ts_percent, 0) >= 0.55 THEN 'Good'
            WHEN COALESCE(ts_percent, 0) >= 0.50 THEN 'Average'
            ELSE 'Below Average'
        END AS shooting_efficiency_tier,
        CASE
            WHEN minutes_played_calc < 5 THEN 'Garbage Time'
            WHEN minutes_played_calc < 15 THEN 'Limited Minutes'
            WHEN (minutes_played_calc >= 30 AND COALESCE(usg_percent, 0) >= 22) OR
                 (minutes_played_calc >= 25 AND COALESCE(usg_percent, 0) >= 25) THEN 'Primary Option'
            WHEN minutes_played_calc >= 20 AND COALESCE(usg_percent, 0) >= 20 THEN 'Secondary Option'
            WHEN minutes_played_calc >= 15 THEN 'Role Player'
            ELSE 'Limited Minutes'
        END AS usage_tier,
        CASE
            WHEN minutes_played_calc < 5 THEN 'Insufficient Minutes'
            WHEN COALESCE(bpm, 0) >= 10 THEN 'Elite Impact'
            WHEN COALESCE(bpm, 0) >= 5 THEN 'High Impact'
            WHEN COALESCE(bpm, 0) >= 0 THEN 'Positive Impact'
            WHEN COALESCE(bpm, 0) >= -5 THEN 'Negative Impact'
            ELSE 'Very Negative Impact'
        END AS impact_tier,
        CASE
            WHEN minutes_played_calc >= 32 THEN 'Starter/Key Player'
            WHEN minutes_played_calc >= 20 THEN 'Rotation Player'
            WHEN minutes_played_calc >= 10 THEN 'Bench Player'
            WHEN minutes_played_calc >= 5 THEN 'Deep Bench'
            ELSE 'Garbage Time'
        END AS minutes_based_role,
        CASE
            WHEN minutes_played_calc >= 15
                AND COALESCE(ast_percent, 0) >= 20
                AND COALESCE(trb_percent, 0) >= 15 THEN TRUE
            ELSE FALSE
        END AS is_versatile,
        CASE
            WHEN minutes_played_calc >= 15
                AND (COALESCE(stl_percent, 0) >= 2.5 OR COALESCE(blk_percent, 0) >= 4)
                AND COALESCE(d_rtg, 0) < 105 THEN TRUE
            ELSE FALSE
        END AS is_defensive_specialist,
        CASE
            WHEN minutes_played_calc >= 15
                AND COALESCE(three_p_ar, 0) >= 0.4
                AND COALESCE(d_rtg, 0) < 110 THEN TRUE
            ELSE FALSE
        END AS is_three_and_d,
        created_at,
        updated_at,
        CURRENT_TIMESTAMP AS dbt_loaded_at
    FROM with_minutes
    WHERE game_id IS NOT NULL AND player_id IS NOT NULL
)

SELECT * FROM cleaned
