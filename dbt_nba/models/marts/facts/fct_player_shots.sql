{{
    config(
        materialized='incremental',
        schema='marts',
        unique_key='shot_key',
        tags=["fact"]
    )
}}

WITH shots_enriched AS (
    SELECT *
    FROM {{ ref('int_player_shots_enriched') }}
    WHERE has_game_match = TRUE
    {% if is_incremental() %}
      AND game_date >= (SELECT MAX(game_date) FROM {{ this }}) - INTERVAL '30 days'
    {% endif %}
),

final AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['se.shot_id', 'se.shot_source']) }} AS shot_key,
        p.player_key,
        t.team_key,
        opp_t.team_key AS opponent_key,
        d.date_key,
        s.season_key,
        se.game_id,
        se.shot_id,
        se.shot_source,
        se.is_playoff,
        se.team_location,
        se.game_result,
        se.quarter_number,
        se.is_overtime_shot,
        se.seconds_remaining_in_quarter,
        se.shot_x_coordinate,
        se.shot_y_coordinate,
        se.is_made,
        se.shot_made_flag,
        se.shot_missed_flag,
        se.shot_type_raw AS shot_type,
        se.shot_point_value,
        se.is_three_pointer,
        se.is_free_throw,
        se.distance_ft,
        se.shot_distance_zone,
        se.points_generated,
        se.team_had_lead,
        se.team_score_at_shot,
        se.opponent_score_at_shot,
        se.score_margin_at_shot,
        se.is_clutch_shot,
        CAST(se.game_date AS DATE) AS game_date
    FROM shots_enriched AS se
    LEFT JOIN {{ ref('dim_players') }} AS p ON se.player_id = p.player_id
    LEFT JOIN {{ ref('dim_teams') }} AS t ON se.team = t.team_abbr
    LEFT JOIN {{ ref('dim_teams') }} AS opp_t ON se.opponent = opp_t.team_abbr
    LEFT JOIN {{ ref('dim_dates') }} AS d ON CAST(se.game_date AS DATE) = d.full_date
    LEFT JOIN {{ ref('dim_seasons') }} AS s ON se.season_start_year = s.season_start_year
)

SELECT * FROM final
