{{
    config(
        materialized='view',
        schema='staging'
    )
}}

WITH source_data AS (
    SELECT *
    FROM {{ source('raw_nba', 'player_shot_charts') }}
    WHERE deleted_at IS NULL
),

cleaned AS (
    SELECT
        id AS shot_id,
        player_id,
        season AS season_year,
        CASE
            WHEN date IS NOT NULL AND date != '' THEN
                strptime(TRIM(date), '%b %d,%Y')::DATE
            ELSE NULL
        END AS game_date,
        date AS game_date_raw,
        CASE
            WHEN date IS NOT NULL AND date != '' THEN
                CASE
                    WHEN EXTRACT(MONTH FROM strptime(TRIM(date), '%b %d,%Y')::DATE) >= 10
                        THEN EXTRACT(YEAR FROM strptime(TRIM(date), '%b %d,%Y')::DATE)::INT
                    ELSE EXTRACT(YEAR FROM strptime(TRIM(date), '%b %d,%Y')::DATE)::INT - 1
                END
            ELSE NULL
        END AS season_start_year,
        qtr AS quarter_raw,
        CASE
            WHEN qtr LIKE '1st%' THEN 1
            WHEN qtr LIKE '2nd%' THEN 2
            WHEN qtr LIKE '3rd%' THEN 3
            WHEN qtr LIKE '4th%' THEN 4
            WHEN qtr ILIKE '%OT%' THEN 5
            ELSE NULL
        END AS quarter_number,
        CASE WHEN qtr ILIKE '%OT%' THEN TRUE ELSE FALSE END AS is_overtime_shot,
        time_remaining AS time_remaining_raw,
        CASE
            WHEN time_remaining IS NOT NULL AND time_remaining LIKE '%:%' THEN
                CAST(SPLIT_PART(time_remaining, ':', 1) AS INT) * 60
                + CAST(SPLIT_PART(time_remaining, ':', 2) AS INT)
            ELSE NULL
        END AS seconds_remaining_in_quarter,
        top AS shot_y_coordinate,
        "left" AS shot_x_coordinate,
        COALESCE(result, FALSE) AS is_made,
        CASE WHEN COALESCE(result, FALSE) = TRUE THEN 1 ELSE 0 END AS shot_made_flag,
        CASE WHEN COALESCE(result, FALSE) = FALSE THEN 1 ELSE 0 END AS shot_missed_flag,
        shot_type AS shot_type_raw,
        CASE
            WHEN shot_type = '3-pointer' THEN 3
            WHEN shot_type = '2-pointer' THEN 2
            ELSE NULL
        END AS shot_point_value,
        CASE WHEN shot_type = '3-pointer' THEN TRUE ELSE FALSE END AS is_three_pointer,
        FALSE AS is_free_throw,
        COALESCE(distance_ft, 0) AS distance_ft,
        CASE
            WHEN COALESCE(distance_ft, 0) <= 3 THEN 'At Rim (0-3 ft)'
            WHEN COALESCE(distance_ft, 0) <= 10 THEN 'Short Range (4-10 ft)'
            WHEN COALESCE(distance_ft, 0) <= 16 THEN 'Mid Range (11-16 ft)'
            WHEN COALESCE(distance_ft, 0) <= 23 THEN 'Long Mid Range (17-23 ft)'
            WHEN COALESCE(distance_ft, 0) <= 27 THEN 'Three Point (24-27 ft)'
            ELSE 'Deep Three (28+ ft)'
        END AS shot_distance_zone,
        COALESCE(lead, FALSE) AS team_had_lead,
        COALESCE(team_score, 0) AS team_score_at_shot,
        COALESCE(opponent_team_score, 0) AS opponent_score_at_shot,
        COALESCE(team_score, 0) - COALESCE(opponent_team_score, 0) AS score_margin_at_shot,
        CASE
            WHEN qtr LIKE '4th%'
                AND time_remaining IS NOT NULL
                AND time_remaining LIKE '%:%'
                AND (CAST(SPLIT_PART(time_remaining, ':', 1) AS INT) * 60
                     + CAST(SPLIT_PART(time_remaining, ':', 2) AS INT)) <= 300
                AND ABS(COALESCE(team_score, 0) - COALESCE(opponent_team_score, 0)) <= 5
            THEN TRUE
            ELSE FALSE
        END AS is_clutch_shot,
        team AS team_abbr_raw,
        opponent AS opponent_abbr_raw,
        CASE
            WHEN COALESCE(result, FALSE) = TRUE THEN
                CASE
                    WHEN shot_type = '3-pointer' THEN 3
                    WHEN shot_type = '2-pointer' THEN 2
                    ELSE 0
                END
            ELSE 0
        END AS points_generated,
        created_at,
        updated_at,
        CURRENT_TIMESTAMP AS dbt_loaded_at
    FROM source_data
    WHERE id IS NOT NULL AND player_id IS NOT NULL AND date IS NOT NULL AND team IS NOT NULL
)

SELECT * FROM cleaned
