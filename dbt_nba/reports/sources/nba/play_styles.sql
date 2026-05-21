select
  shot_selection_style,
  count(*) as games,
  round(avg(case when game_result = 'W' then 1.0 else 0.0 end) * 100, 1) as win_pct,
  round(avg(offensive_rating), 1) as avg_off_rating
from main_intermediate.int_team_performance
where season_start_year = (select max(season_start_year) from main_intermediate.int_team_performance)
group by shot_selection_style
order by avg_off_rating desc
