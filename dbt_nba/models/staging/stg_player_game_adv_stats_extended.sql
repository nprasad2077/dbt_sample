{{
    config(
        materialized='table',
        schema='staging',
        tags=["staging"]
    )
}}

{% set minutes_insufficient = 5 %}

WITH source_data AS (
    SELECT * FROM {{ source('raw_nba', 'player_game_adv_stats') }}
    WHERE deleted_at IS NULL
),

games AS (
    SELECT game_id, season_start_year
    FROM {{ ref('stg_games') }}
),

with_minutes AS (
    SELECT
        sd.*,
        g.season_start_year,
        CASE
            WHEN sd.mp IS NOT NULL AND sd.mp != '' AND sd.mp LIKE '%:%' THEN
                CAST(SPLIT_PART(sd.mp, ':', 1) AS DECIMAL)
                + (CAST(SPLIT_PART(sd.mp, ':', 2) AS DECIMAL) / 60.0)
            WHEN sd.mp IS NOT NULL AND sd.mp != '' AND regexp_matches(sd.mp, '^[0-9\.]+$') THEN
                CAST(sd.mp AS DECIMAL)
            ELSE 0
        END AS minutes_played
    FROM source_data AS sd
    LEFT JOIN games AS g ON sd.game_id = g.game_id
),

season_thresholds AS (
    SELECT * FROM {{ ref('stg_season_thresholds') }}
),

cleaned AS (
    SELECT
        wm.game_id,
        wm.player_id,
        wm.team,
        wm.player_name,
        wm.mp AS minutes_played_str,
        wm.minutes_played,
        COALESCE(wm.ts_percent, 0) AS true_shooting_pct,
        COALESCE(wm.efg_percent, 0) AS effective_fg_pct,
        COALESCE(wm.three_p_ar, 0) AS three_point_attempt_rate,
        COALESCE(wm.f_tr, 0) AS free_throw_rate,
        COALESCE(wm.orb_percent, 0) AS offensive_rebound_pct,
        COALESCE(wm.drb_percent, 0) AS defensive_rebound_pct,
        COALESCE(wm.trb_percent, 0) AS total_rebound_pct,
        COALESCE(wm.ast_percent, 0) AS assist_pct,
        COALESCE(wm.stl_percent, 0) AS steal_pct,
        COALESCE(wm.blk_percent, 0) AS block_pct,
        COALESCE(wm.tov_percent, 0) AS turnover_pct,
        COALESCE(wm.usg_percent, 0) AS usage_pct,
        COALESCE(wm.o_rtg, 0) AS offensive_rating,
        COALESCE(wm.d_rtg, 0) AS defensive_rating,
        COALESCE(wm.bpm, 0) AS box_plus_minus,
        COALESCE(wm.o_rtg, 0) - COALESCE(wm.d_rtg, 0) AS net_rating,

        -- Minutes-based role
        CASE
            WHEN wm.minutes_played >= t.min_p95 THEN 'Elite Minutes (Top 5%)'
            WHEN wm.minutes_played >= t.min_p90 THEN 'Elite Minutes (Top 10%)'
            WHEN wm.minutes_played >= t.min_q3 THEN 'Starter'
            WHEN wm.minutes_played >= t.min_median THEN 'Key Rotation'
            WHEN wm.minutes_played >= t.min_q1 THEN 'Regular Rotation'
            WHEN wm.minutes_played >= t.min_p5 THEN 'Deep Bench'
            WHEN wm.minutes_played >= {{ minutes_insufficient }} THEN 'Garbage Time'
            ELSE 'Insufficient Minutes'
        END AS minutes_based_role,

        CASE
            WHEN wm.minutes_played < {{ minutes_insufficient }} THEN 'Insufficient'
            WHEN wm.minutes_played < t.min_q1 THEN 'Q1'
            WHEN wm.minutes_played < t.min_median THEN 'Q2'
            WHEN wm.minutes_played < t.min_q3 THEN 'Q3'
            ELSE 'Q4'
        END AS minutes_quartile,

        -- Usage Tier
        CASE
            WHEN wm.minutes_played < {{ minutes_insufficient }} THEN 'Insufficient Minutes'
            WHEN COALESCE(wm.usg_percent, 0) >= t.usg_p90
                AND wm.minutes_played >= t.min_q1 THEN 'Heliocentric Option'
            WHEN COALESCE(wm.usg_percent, 0) >= t.usg_q3
                AND wm.minutes_played >= t.min_q3 THEN 'Primary Option'
            WHEN COALESCE(wm.usg_percent, 0) >= t.usg_median
                AND wm.minutes_played >= t.min_median THEN 'Secondary Option'
            WHEN COALESCE(wm.usg_percent, 0) >= t.usg_q1
                AND wm.minutes_played >= t.min_q1 THEN 'Role Player'
            WHEN wm.minutes_played >= t.min_q1
                AND COALESCE(wm.usg_percent, 0) >= t.usg_p5 THEN 'Connector/Specialist'
            WHEN wm.minutes_played >= t.min_p5 THEN 'Low Usage Player'
            ELSE 'Limited Role'
        END AS usage_tier,

        CASE
            WHEN COALESCE(wm.usg_percent, 0) < t.usg_q1 THEN 'Q1'
            WHEN COALESCE(wm.usg_percent, 0) < t.usg_median THEN 'Q2'
            WHEN COALESCE(wm.usg_percent, 0) < t.usg_q3 THEN 'Q3'
            ELSE 'Q4'
        END AS usage_quartile,

        -- Impact Tier
        CASE
            WHEN wm.minutes_played < {{ minutes_insufficient }} THEN 'Insufficient Minutes'
            WHEN COALESCE(wm.bpm, 0) >= t.bpm_p90 THEN 'Elite Impact'
            WHEN COALESCE(wm.bpm, 0) >= t.bpm_q3 THEN 'High Impact'
            WHEN COALESCE(wm.bpm, 0) >= t.bpm_median THEN 'Positive Impact'
            WHEN COALESCE(wm.bpm, 0) >= t.bpm_q1 THEN 'Neutral Impact'
            WHEN COALESCE(wm.bpm, 0) >= t.bpm_p5 THEN 'Negative Impact'
            ELSE 'Very Negative Impact'
        END AS impact_tier,

        CASE
            WHEN COALESCE(wm.bpm, 0) < t.bpm_q1 THEN 'Q1'
            WHEN COALESCE(wm.bpm, 0) < t.bpm_median THEN 'Q2'
            WHEN COALESCE(wm.bpm, 0) < t.bpm_q3 THEN 'Q3'
            ELSE 'Q4'
        END AS bpm_quartile,

        -- Shooting efficiency tier
        CASE
            WHEN wm.minutes_played < {{ minutes_insufficient }} THEN 'Insufficient Minutes'
            WHEN COALESCE(wm.ts_percent, 0) >= t.ts_q3 THEN 'Elite'
            WHEN COALESCE(wm.ts_percent, 0) >= t.ts_median THEN 'Good'
            WHEN COALESCE(wm.ts_percent, 0) >= t.ts_q1 THEN 'Average'
            ELSE 'Below Average'
        END AS shooting_efficiency_tier,

        -- Boolean flags
        wm.minutes_played >= t.min_p90 AS is_extreme_minutes,
        wm.minutes_played >= t.min_q3 AS is_starter_minutes,
        wm.minutes_played >= t.min_q1 AS is_meaningful_minutes,

        wm.minutes_played >= t.min_q1
            AND COALESCE(wm.ast_percent, 0) >= 20
            AND COALESCE(wm.trb_percent, 0) >= 13 AS is_versatile,

        wm.minutes_played >= t.min_q1
            AND (COALESCE(wm.stl_percent, 0) >= 2.5 OR COALESCE(wm.blk_percent, 0) >= 3)
            AND COALESCE(wm.d_rtg, 0) <= 110 AS is_defensive_specialist,

        wm.minutes_played >= t.min_q1
            AND COALESCE(wm.three_p_ar, 0) >= 0.4
            AND COALESCE(wm.d_rtg, 0) <= 110 AS is_three_and_d,

        COALESCE(wm.usg_percent, 0) >= t.usg_p90 AS is_extreme_usage,
        COALESCE(wm.usg_percent, 0) >= t.usg_q3 AS is_high_usage,
        COALESCE(wm.bpm, 0) >= t.bpm_p90 AS is_elite_impact,
        COALESCE(wm.bpm, 0) >= t.bpm_q3 AS is_positive_impact,

        wm.created_at,
        wm.updated_at,
        CURRENT_TIMESTAMP AS dbt_loaded_at

    FROM with_minutes AS wm
    LEFT JOIN season_thresholds AS t
        ON wm.season_start_year = t.season_start_year
    WHERE wm.game_id IS NOT NULL AND wm.player_id IS NOT NULL
)

SELECT * FROM cleaned
