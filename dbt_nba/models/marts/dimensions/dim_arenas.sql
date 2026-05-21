{{
    config(
        materialized='table',
        schema='marts',
        tags=["dimension"]
    )
}}

WITH source AS (
    SELECT arena_name, city, state_or_country, location
    FROM {{ ref('arena_mappings') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['arena_name', 'city']) }} AS arena_key,
    arena_name,
    city AS arena_city,
    state_or_country AS arena_state_or_country,
    location AS arena_location
FROM source
ORDER BY arena_name, arena_city
