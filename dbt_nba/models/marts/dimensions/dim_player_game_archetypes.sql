{{
    config(
        materialized='table',
        schema='marts',
        tags=["dimension"]
    )
}}

WITH distinct_archetypes AS (
    SELECT DISTINCT
        usage_tier,
        impact_tier,
        shooting_efficiency_tier,
        minutes_based_role,
        is_double_double,
        is_triple_double,
        is_versatile,
        is_defensive_specialist,
        is_three_and_d
    FROM {{ ref('int_player_performance') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'usage_tier',
        'impact_tier',
        'shooting_efficiency_tier',
        'minutes_based_role',
        'is_double_double',
        'is_triple_double',
        'is_versatile',
        'is_defensive_specialist',
        'is_three_and_d'
    ]) }} AS archetype_key,
    *
FROM distinct_archetypes
