select
  p.player_name,
  count(*) as games_played,
  round(avg(ps.points), 1) as ppg,
  round(avg(ps.total_rebounds), 1) as rpg,
  round(avg(ps.assists), 1) as apg,
  round(avg(ps.true_shooting_pct) * 100, 1) as ts_pct
from main_marts.fct_player_game_stats ps
left join main_marts.dim_players p on ps.player_key = p.player_key
group by p.player_name
having count(*) >= 50
order by ppg desc
limit 20
