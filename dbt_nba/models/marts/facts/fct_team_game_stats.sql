{{
    config(
        materialized='incremental',
        schema='marts',
        tags=["fact"],
        unique_key='team_game_key'
    )
}}

WITH team_performance AS (
    SELECT * FROM {{ ref('int_team_performance') }}
),

game_details AS (
    SELECT
        game_id, game_date, season_start_year,
        home_team, visitor_team, arena AS arena_name, arena_city
    FROM {{ ref('int_games_enriched') }}
),

final AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['tp.game_id', 'tp.team']) }} AS team_game_key,
        t.team_key,
        d.date_key,
        s.season_key,
        a.arena_key,
        opp.team_key AS opponent_key,
        tp.game_id,
        (tp.team = gd.home_team) AS is_home_team,
        tp.points,
        tp.offensive_rating,
        tp.defensive_rating,
        tp.net_rating,
        tp.pace,
        tp.effective_fg_pct,
        tp.turnover_rate,
        tp.offensive_tier,
        tp.defensive_tier,
        CAST(gd.game_date AS DATE) AS game_date
    FROM team_performance AS tp
    LEFT JOIN game_details AS gd ON tp.game_id = gd.game_id
    LEFT JOIN {{ ref('dim_teams') }} AS t ON tp.team = t.team_abbr
    LEFT JOIN {{ ref('dim_teams') }} AS opp
        ON CASE WHEN tp.team = gd.home_team THEN gd.visitor_team ELSE gd.home_team END = opp.team_abbr
    LEFT JOIN {{ ref('dim_dates') }} AS d ON CAST(gd.game_date AS DATE) = d.full_date
    LEFT JOIN {{ ref('dim_seasons') }} AS s ON gd.season_start_year = s.season_start_year
    LEFT JOIN {{ ref('dim_arenas') }} AS a ON gd.arena_name = a.arena_name AND gd.arena_city = a.arena_city
    {% if is_incremental() %}
    WHERE gd.game_date >= (SELECT MAX(game_date) FROM {{ this }}) - INTERVAL '30 days'
    {% endif %}
)

SELECT * FROM final
