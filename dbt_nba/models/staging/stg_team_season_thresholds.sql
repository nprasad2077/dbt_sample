{{
    config(
        materialized='table',
        schema='staging',
        tags=["staging"]
    )
}}

WITH team_stats AS (
    SELECT
        g.season_start_year,
        COALESCE(s.o_rtg, 0) AS offensive_rating,
        COALESCE(s.d_rtg, 0) AS defensive_rating,
        COALESCE(s.three_p_ar, 0) AS three_point_attempt_rate,
        COALESCE(s.ast_percent, 0) AS assist_pct,
        COALESCE(s.orb_percent, 0) AS offensive_rebound_pct,
        COALESCE(s.drb_percent, 0) AS defensive_rebound_pct,
        COALESCE(s.tov_percent, 0) AS turnover_pct,
        COALESCE(s.stl_percent, 0) + COALESCE(s.blk_percent, 0) AS stl_blk_combined,
        COALESCE(s.ts_percent, 0) AS true_shooting_pct,
        COALESCE(s.f_tr, 0) AS free_throw_rate
    FROM {{ source('raw_nba', 'team_game_adv_stats') }} AS s
    INNER JOIN {{ ref('stg_games') }} AS g
        ON s.game_id = g.game_id
    WHERE s.deleted_at IS NULL
      AND s.game_id IS NOT NULL
      AND s.team IS NOT NULL
)

SELECT
    season_start_year,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY offensive_rating) AS ortg_p10,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY offensive_rating) AS ortg_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY offensive_rating) AS ortg_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY offensive_rating) AS ortg_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY offensive_rating) AS ortg_p90,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY defensive_rating) AS drtg_p10,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY defensive_rating) AS drtg_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY defensive_rating) AS drtg_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY defensive_rating) AS drtg_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY defensive_rating) AS drtg_p90,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY three_point_attempt_rate) AS tpar_p10,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY three_point_attempt_rate) AS tpar_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY three_point_attempt_rate) AS tpar_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY three_point_attempt_rate) AS tpar_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY three_point_attempt_rate) AS tpar_p90,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY assist_pct) AS ast_p10,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY assist_pct) AS ast_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY assist_pct) AS ast_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY assist_pct) AS ast_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY assist_pct) AS ast_p90,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY offensive_rebound_pct) AS orb_p10,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY offensive_rebound_pct) AS orb_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY offensive_rebound_pct) AS orb_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY offensive_rebound_pct) AS orb_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY offensive_rebound_pct) AS orb_p90,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY defensive_rebound_pct) AS drb_p10,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY defensive_rebound_pct) AS drb_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY defensive_rebound_pct) AS drb_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY defensive_rebound_pct) AS drb_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY defensive_rebound_pct) AS drb_p90,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY turnover_pct) AS tov_p10,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY turnover_pct) AS tov_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY turnover_pct) AS tov_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY turnover_pct) AS tov_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY turnover_pct) AS tov_p90,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY stl_blk_combined) AS stl_blk_p10,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY stl_blk_combined) AS stl_blk_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY stl_blk_combined) AS stl_blk_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY stl_blk_combined) AS stl_blk_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY stl_blk_combined) AS stl_blk_p90,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY true_shooting_pct) AS ts_p10,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY true_shooting_pct) AS ts_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY true_shooting_pct) AS ts_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY true_shooting_pct) AS ts_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY true_shooting_pct) AS ts_p90,
    PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY free_throw_rate) AS ftr_p10,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY free_throw_rate) AS ftr_q1,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY free_throw_rate) AS ftr_median,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY free_throw_rate) AS ftr_q3,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY free_throw_rate) AS ftr_p90
FROM team_stats
GROUP BY season_start_year
ORDER BY season_start_year
