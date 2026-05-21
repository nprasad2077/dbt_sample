{{
    config(
        materialized='incremental',
        schema='marts',
        unique_key='player_game_key',
        tags=["fact"]
    )
}}

WITH player_performance AS (
    SELECT * FROM {{ ref('int_player_performance') }}
),

game_details AS (
    SELECT game_id, arena AS arena_name, arena_city
    FROM {{ ref('int_games_enriched') }}
),

final AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['pp.game_id', 'pp.player_id']) }} AS player_game_key,
        p.player_key,
        t.team_key,
        d.date_key,
        s.season_key,
        a.arena_key,
        arch.archetype_key,
        pp.game_id,
        pp.minutes_played,
        pp.points,
        pp.assists,
        pp.total_rebounds,
        pp.steals,
        pp.blocks,
        pp.turnovers,
        pp.plus_minus,
        pp.net_rating,
        pp.box_plus_minus,
        pp.field_goals_made,
        pp.field_goals_attempted,
        pp.three_pointers_made,
        pp.three_pointers_attempted,
        pp.true_shooting_pct,
        pp.effective_fg_pct,
        pp.usage_pct,
        pp.offensive_rating,
        pp.defensive_rating,
        CAST(pp.game_date AS DATE) AS game_date
    FROM player_performance AS pp
    LEFT JOIN game_details AS gd ON pp.game_id = gd.game_id
    LEFT JOIN {{ ref('dim_player_game_archetypes') }} AS arch
        ON pp.usage_tier = arch.usage_tier
        AND pp.impact_tier = arch.impact_tier
        AND pp.shooting_efficiency_tier = arch.shooting_efficiency_tier
        AND pp.minutes_based_role = arch.minutes_based_role
        AND pp.is_double_double = arch.is_double_double
        AND pp.is_triple_double = arch.is_triple_double
        AND pp.is_versatile = arch.is_versatile
        AND pp.is_defensive_specialist = arch.is_defensive_specialist
        AND pp.is_three_and_d = arch.is_three_and_d
    LEFT JOIN {{ ref('dim_players') }} AS p ON pp.player_id = p.player_id
    LEFT JOIN {{ ref('dim_teams') }} AS t ON pp.team = t.team_abbr
    LEFT JOIN {{ ref('dim_dates') }} AS d ON CAST(pp.game_date AS DATE) = d.full_date
    LEFT JOIN {{ ref('dim_seasons') }} AS s ON pp.season_start_year = s.season_start_year
    LEFT JOIN {{ ref('dim_arenas') }} AS a ON gd.arena_name = a.arena_name AND gd.arena_city = a.arena_city
    {% if is_incremental() %}
    WHERE pp.game_date >= (SELECT MAX(game_date) FROM {{ this }}) - INTERVAL '30 days'
    {% endif %}
)

SELECT * FROM final
