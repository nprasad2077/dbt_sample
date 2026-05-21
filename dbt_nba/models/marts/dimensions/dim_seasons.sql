{{
    config(
        materialized='table',
        schema='marts',
        tags=["dimension"]
    )
}}

WITH all_seasons AS (
    SELECT DISTINCT season_start_year
    FROM {{ ref('int_games_enriched') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['season_start_year']) }} AS season_key,
    season_start_year,
    season_start_year || '-' || SUBSTR(CAST(season_start_year + 1 AS VARCHAR), 3, 2) AS season_display
FROM all_seasons
ORDER BY season_start_year
