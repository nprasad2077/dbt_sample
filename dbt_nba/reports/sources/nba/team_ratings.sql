select
  team,
  count(*) as games,
  sum(case when game_result = 'W' then 1 else 0 end) as wins,
  round(100.0 * sum(case when game_result = 'W' then 1 else 0 end) / count(*), 1) as win_pct,
  round(avg(offensive_rating), 1) as avg_off_rating,
  round(avg(defensive_rating), 1) as avg_def_rating,
  round(avg(net_rating), 1) as avg_net_rating,
  round(avg(pace), 1) as avg_pace,
  round(avg(effective_fg_pct) * 100, 1) as avg_efg_pct
from main_intermediate.int_team_performance
where season_start_year = (select max(season_start_year) from main_intermediate.int_team_performance)
group by team
order by avg_net_rating desc
