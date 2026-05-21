select
  player_name,
  team,
  count(*) as games,
  round(avg(points), 1) as ppg,
  round(avg(assists), 1) as apg,
  round(avg(total_rebounds), 1) as rpg,
  round(avg(box_plus_minus), 2) as avg_bpm,
  round(avg(usage_pct), 1) as avg_usage,
  round(avg(true_shooting_pct) * 100, 1) as ts_pct,
  round(avg(net_rating), 1) as avg_net_rating,
  sum(case when is_double_double then 1 else 0 end) as double_doubles,
  sum(case when is_triple_double then 1 else 0 end) as triple_doubles
from main_intermediate.int_player_performance
where season_start_year = (select max(season_start_year) from main_intermediate.int_player_performance)
  and minutes_played >= 20
group by player_name, team
having count(*) >= 20
order by avg_bpm desc
limit 30
