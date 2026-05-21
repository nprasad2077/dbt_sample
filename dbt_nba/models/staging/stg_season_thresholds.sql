{{
    config(
        materialized='table',
        schema='staging',
        tags=["staging"]
    )
}}

WITH player_stats AS (
    SELECT
        g.season_start_year,
        CASE
            WHEN s.mp IS NOT NULL AND s.mp != '' AND s.mp LIKE '%:%' THEN
                CAST(SPLIT_PART(s.mp, ':', 1) AS DECIMAL)
                + (CAST(SPLIT_PART(s.mp, ':', 2) AS DECIMAL) / 60.0)
            WHEN s.mp IS NOT NULL AND s.mp != '' AND regexp_matches(s.mp, '^[0-9\.]+$') THEN
                CAST(s.mp AS DECIMAL)
            ELSE 0
        END AS minutes_played,
        COALESCE(s.usg_percent, 0) AS usage_pct,
        COALESCE(s.bpm, 0) AS bpm,
        COALESCE(s.ts_percent, 0) AS ts_pct
    FROM {{ source('raw_nba', 'player_game_adv_stats') }} AS s
    INNER JOIN {{ ref('stg_games') }} AS g
        ON s.game_id = g.game_id
    WHERE s.deleted_at IS NULL
      AND s.game_id IS NOT NULL
      AND s.player_id IS NOT NULL
)

SELECT
    season_start_year,
    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY minutes_played) AS min_p5,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY minutes_played) AS min_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY minutes_played) AS min_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY minutes_played) AS min_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY minutes_played) AS min_p90,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY minutes_played) AS min_p95,
    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY usage_pct) AS usg_p5,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY usage_pct) AS usg_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY usage_pct) AS usg_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY usage_pct) AS usg_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY usage_pct) AS usg_p90,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY usage_pct) AS usg_p95,
    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY bpm) AS bpm_p5,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY bpm) AS bpm_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY bpm) AS bpm_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY bpm) AS bpm_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY bpm) AS bpm_p90,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY bpm) AS bpm_p95,
    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY ts_pct) AS ts_p5,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY ts_pct) AS ts_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY ts_pct) AS ts_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY ts_pct) AS ts_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY ts_pct) AS ts_p90,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ts_pct) AS ts_p95
FROM player_stats
GROUP BY season_start_year
ORDER BY season_start_year
