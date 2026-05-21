select
  player_name,
  team,
  count(*) as games,
  round(avg(usage_pct), 1) as usage,
  round(avg(true_shooting_pct) * 100, 1) as efficiency,
  round(avg(points), 1) as ppg
from main_intermediate.int_player_performance
where season_start_year = (select max(season_start_year) from main_intermediate.int_player_performance)
  and minutes_played >= 20
group by player_name, team
having count(*) >= 20
order by usage desc
