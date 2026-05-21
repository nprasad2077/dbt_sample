select
  s.season_display,
  count(*) as total_games,
  sum(case when g.is_overtime then 1 else 0 end) as overtime_games,
  sum(case when g.is_playoff then 1 else 0 end) as playoff_games,
  round(avg(g.total_points), 1) as avg_total_points,
  round(avg(g.point_differential), 1) as avg_margin
from main_marts.fct_game_results g
left join main_marts.dim_seasons s on g.season_key = s.season_key
group by s.season_display
order by s.season_display desc
