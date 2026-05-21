select
  s.season_display,
  count(*) as total_games,
  sum(case when g.is_home_team_winner then 1 else 0 end) as home_wins,
  round(100.0 * sum(case when g.is_home_team_winner then 1 else 0 end) / count(*), 1) as home_win_pct
from main_marts.fct_game_results g
left join main_marts.dim_seasons s on g.season_key = s.season_key
group by s.season_display
order by s.season_display
