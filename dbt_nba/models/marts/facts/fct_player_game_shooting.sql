{{
    config(
        materialized='incremental',
        schema='marts',
        unique_key='player_game_shooting_key',
        tags=["fact"]
    )
}}

WITH shots AS (
    SELECT *
    FROM {{ ref('int_player_shots_enriched') }}
    WHERE has_game_match = TRUE
    {% if is_incremental() %}
      AND game_date >= (SELECT MAX(game_date) FROM {{ this }}) - INTERVAL '30 days'
    {% endif %}
),

game_agg AS (
    SELECT
        game_id, player_id, team, opponent,
        MIN(game_date) AS game_date,
        MIN(season_start_year) AS season_start_year,
        BOOL_OR(is_playoff) AS is_playoff,
        MIN(team_location) AS team_location,
        MIN(game_result) AS game_result,

        SUM(points_generated) AS total_points,
        COUNT(*) AS total_shot_attempts,
        SUM(shot_made_flag) AS total_shots_made,

        COUNT(*) FILTER (WHERE shot_source = 'shot_chart') AS fg_attempts,
        SUM(shot_made_flag) FILTER (WHERE shot_source = 'shot_chart') AS fg_makes,
        CASE WHEN COUNT(*) FILTER (WHERE shot_source = 'shot_chart') > 0
            THEN SUM(shot_made_flag) FILTER (WHERE shot_source = 'shot_chart')::DECIMAL
                 / COUNT(*) FILTER (WHERE shot_source = 'shot_chart')::DECIMAL
            ELSE 0
        END AS fg_pct,
        SUM(points_generated) FILTER (WHERE shot_source = 'shot_chart') AS fg_points,

        COUNT(*) FILTER (WHERE shot_source = 'box_score_ft') AS ft_attempts,
        SUM(shot_made_flag) FILTER (WHERE shot_source = 'box_score_ft') AS ft_makes,
        CASE WHEN COUNT(*) FILTER (WHERE shot_source = 'box_score_ft') > 0
            THEN SUM(shot_made_flag) FILTER (WHERE shot_source = 'box_score_ft')::DECIMAL
                 / COUNT(*) FILTER (WHERE shot_source = 'box_score_ft')::DECIMAL
            ELSE 0
        END AS ft_pct,
        SUM(points_generated) FILTER (WHERE shot_source = 'box_score_ft') AS ft_points,

        COUNT(*) FILTER (WHERE is_three_pointer = FALSE AND shot_source = 'shot_chart') AS two_point_attempts,
        SUM(shot_made_flag) FILTER (WHERE is_three_pointer = FALSE AND shot_source = 'shot_chart') AS two_point_makes,
        CASE WHEN COUNT(*) FILTER (WHERE is_three_pointer = FALSE AND shot_source = 'shot_chart') > 0
            THEN SUM(shot_made_flag) FILTER (WHERE is_three_pointer = FALSE AND shot_source = 'shot_chart')::DECIMAL
                 / COUNT(*) FILTER (WHERE is_three_pointer = FALSE AND shot_source = 'shot_chart')::DECIMAL
            ELSE 0
        END AS two_point_fg_pct,

        COUNT(*) FILTER (WHERE is_three_pointer = TRUE) AS three_point_attempts,
        SUM(shot_made_flag) FILTER (WHERE is_three_pointer = TRUE) AS three_point_makes,
        CASE WHEN COUNT(*) FILTER (WHERE is_three_pointer = TRUE) > 0
            THEN SUM(shot_made_flag) FILTER (WHERE is_three_pointer = TRUE)::DECIMAL
                 / COUNT(*) FILTER (WHERE is_three_pointer = TRUE)::DECIMAL
            ELSE 0
        END AS three_point_fg_pct,

        COUNT(*) FILTER (WHERE shot_distance_zone = 'At Rim (0-3 ft)') AS at_rim_attempts,
        SUM(shot_made_flag) FILTER (WHERE shot_distance_zone = 'At Rim (0-3 ft)') AS at_rim_makes,
        CASE WHEN COUNT(*) FILTER (WHERE shot_distance_zone = 'At Rim (0-3 ft)') > 0
            THEN SUM(shot_made_flag) FILTER (WHERE shot_distance_zone = 'At Rim (0-3 ft)')::DECIMAL
                 / COUNT(*) FILTER (WHERE shot_distance_zone = 'At Rim (0-3 ft)')::DECIMAL
            ELSE 0
        END AS at_rim_fg_pct,

        COUNT(*) FILTER (WHERE is_clutch_shot = TRUE) AS clutch_fg_attempts,
        SUM(shot_made_flag) FILTER (WHERE is_clutch_shot = TRUE) AS clutch_fg_makes,
        CASE WHEN COUNT(*) FILTER (WHERE is_clutch_shot = TRUE) > 0
            THEN SUM(shot_made_flag) FILTER (WHERE is_clutch_shot = TRUE)::DECIMAL
                 / COUNT(*) FILTER (WHERE is_clutch_shot = TRUE)::DECIMAL
            ELSE 0
        END AS clutch_fg_pct,

        CASE WHEN COUNT(*) FILTER (WHERE shot_source = 'shot_chart') > 0
            THEN COUNT(*) FILTER (WHERE is_three_pointer = TRUE)::DECIMAL
                 / COUNT(*) FILTER (WHERE shot_source = 'shot_chart')::DECIMAL
            ELSE 0
        END AS three_point_rate,

        CASE WHEN COUNT(*) FILTER (WHERE shot_source = 'shot_chart') > 0
            THEN COUNT(*) FILTER (WHERE shot_distance_zone = 'At Rim (0-3 ft)')::DECIMAL
                 / COUNT(*) FILTER (WHERE shot_source = 'shot_chart')::DECIMAL
            ELSE 0
        END AS at_rim_rate,

        CASE WHEN COUNT(*) FILTER (WHERE shot_source = 'shot_chart') > 0
            THEN COUNT(*) FILTER (WHERE shot_distance_zone IN ('Mid Range (11-16 ft)', 'Long Mid Range (17-23 ft)'))::DECIMAL
                 / COUNT(*) FILTER (WHERE shot_source = 'shot_chart')::DECIMAL
            ELSE 0
        END AS mid_range_rate,

        AVG(distance_ft) FILTER (WHERE shot_source = 'shot_chart') AS avg_fg_distance_ft,

        CASE WHEN (
                COUNT(*) FILTER (WHERE shot_source = 'shot_chart')
                + 0.44 * COUNT(*) FILTER (WHERE shot_source = 'box_score_ft')
            ) > 0
            THEN SUM(points_generated)::DECIMAL / (
                2.0 * (
                    COUNT(*) FILTER (WHERE shot_source = 'shot_chart')
                    + 0.44 * COUNT(*) FILTER (WHERE shot_source = 'box_score_ft')
                )
            )
            ELSE 0
        END AS true_shooting_pct

    FROM shots
    GROUP BY game_id, player_id, team, opponent
),

final AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['ga.game_id', 'ga.player_id']) }} AS player_game_shooting_key,
        p.player_key,
        t.team_key,
        opp_t.team_key AS opponent_key,
        d.date_key,
        s.season_key,
        ga.game_id,
        ga.is_playoff,
        ga.team_location,
        ga.game_result,
        ga.total_points,
        ga.total_shot_attempts,
        ga.total_shots_made,
        ga.fg_attempts,
        ga.fg_makes,
        ga.fg_pct,
        ga.fg_points,
        ga.ft_attempts,
        ga.ft_makes,
        ga.ft_pct,
        ga.ft_points,
        ga.true_shooting_pct,
        ga.two_point_attempts,
        ga.two_point_makes,
        ga.two_point_fg_pct,
        ga.three_point_attempts,
        ga.three_point_makes,
        ga.three_point_fg_pct,
        ga.at_rim_attempts,
        ga.at_rim_makes,
        ga.at_rim_fg_pct,
        ga.clutch_fg_attempts,
        ga.clutch_fg_makes,
        ga.clutch_fg_pct,
        ga.three_point_rate,
        ga.at_rim_rate,
        ga.mid_range_rate,
        ga.avg_fg_distance_ft,
        CASE
            WHEN ga.three_point_rate >= 0.50 THEN 'Perimeter Heavy'
            WHEN ga.at_rim_rate >= 0.50 THEN 'Rim Attacker'
            WHEN ga.mid_range_rate >= 0.40 THEN 'Mid Range Heavy'
            WHEN ga.three_point_rate >= 0.35 AND ga.at_rim_rate >= 0.30 THEN 'Modern (Rim & Three)'
            ELSE 'Balanced'
        END AS shot_profile_type,
        CAST(ga.game_date AS DATE) AS game_date
    FROM game_agg AS ga
    LEFT JOIN {{ ref('dim_players') }} AS p ON ga.player_id = p.player_id
    LEFT JOIN {{ ref('dim_teams') }} AS t ON ga.team = t.team_abbr
    LEFT JOIN {{ ref('dim_teams') }} AS opp_t ON ga.opponent = opp_t.team_abbr
    LEFT JOIN {{ ref('dim_dates') }} AS d ON CAST(ga.game_date AS DATE) = d.full_date
    LEFT JOIN {{ ref('dim_seasons') }} AS s ON ga.season_start_year = s.season_start_year
)

SELECT * FROM final
