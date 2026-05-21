{{
    config(
        materialized='table',
        schema='marts',
        tags=["dimension"]
    )
}}

WITH team_mappings AS (
    SELECT team_abbr, full_name
    FROM {{ ref('team_maps') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['team_abbr']) }} AS team_key,
    team_abbr,
    full_name AS team_full_name
FROM team_mappings
ORDER BY team_abbr
