{{
    config(
        materialized='incremental',
        schema='marts',
        unique_key='quarter_scoring_key',
        tags=["fact"]
    )
}}

WITH games AS (
    SELECT game_id, game_date, season_start_year
    FROM {{ ref('int_games_enriched') }}
    {% if is_incremental() %}
    WHERE game_date >= (SELECT MAX(game_date) FROM {{ this }}) - INTERVAL '30 days'
    {% endif %}
),

unpivoted_scores AS (
    {{ dbt_utils.unpivot(
        relation=ref('stg_line_scores'),
        cast_to='INTEGER',
        exclude=['game_id', 'team', 'total_points', 'first_half_points', 'second_half_points', 'regulation_points', 'overtime_points', 'had_ot1', 'had_ot2', 'had_ot3', 'q2_momentum', 'q3_momentum', 'q4_momentum', 'max_quarter_score', 'min_quarter_score', 'best_quarter', 'created_at', 'updated_at', 'dbt_loaded_at'],
        field_name='period_name',
        value_name='points_scored'
    ) }}
    WHERE game_id IN (SELECT game_id FROM games)
),

final AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['team_scores.game_id', 'team_map.team_abbr', 'team_scores.period_name']) }} AS quarter_scoring_key,
        d.date_key,
        s.season_key,
        t.team_key,
        opp.team_key AS opponent_key,
        team_scores.game_id,
        REPLACE(UPPER(team_scores.period_name), '_POINTS', '') AS period,
        team_scores.points_scored,
        opponent_scores.points_scored AS opponent_points_scored,
        (team_scores.points_scored - opponent_scores.points_scored) AS period_point_differential,
        CAST(g.game_date AS DATE) AS game_date
    FROM unpivoted_scores AS team_scores
    INNER JOIN unpivoted_scores AS opponent_scores
        ON team_scores.game_id = opponent_scores.game_id
        AND team_scores.period_name = opponent_scores.period_name
        AND team_scores.team != opponent_scores.team
    INNER JOIN games AS g ON team_scores.game_id = g.game_id
    LEFT JOIN {{ ref('team_maps') }} AS team_map ON team_scores.team = team_map.team_abbr
    LEFT JOIN {{ ref('team_maps') }} AS opponent_map ON opponent_scores.team = opponent_map.team_abbr
    LEFT JOIN {{ ref('dim_teams') }} AS t ON team_map.team_abbr = t.team_abbr
    LEFT JOIN {{ ref('dim_teams') }} AS opp ON opponent_map.team_abbr = opp.team_abbr
    LEFT JOIN {{ ref('dim_dates') }} AS d ON CAST(g.game_date AS DATE) = d.full_date
    LEFT JOIN {{ ref('dim_seasons') }} AS s ON g.season_start_year = s.season_start_year
    WHERE team_scores.points_scored IS NOT NULL
)

SELECT * FROM final
