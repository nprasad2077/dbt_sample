{{
    config(
        materialized='table',
        schema='marts',
        tags=["dimension"]
    )
}}

WITH player_game_stats AS (
    SELECT
        stats.player_id,
        stats.player_name,
        games.game_date,
        ROW_NUMBER() OVER (PARTITION BY stats.player_id ORDER BY games.game_date DESC) as rn
    FROM {{ ref('stg_player_game_basic_stats') }} AS stats
    LEFT JOIN {{ ref('stg_games') }} AS games
        ON stats.game_id = games.game_id
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['player_id']) }} AS player_key,
    player_id,
    player_name
FROM player_game_stats
WHERE rn = 1
ORDER BY player_name
