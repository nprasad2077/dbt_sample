select
  g.game_date,
  g.home_points,
  g.visitor_points,
  g.total_points,
  g.point_differential,
  g.is_overtime,
  g.is_playoff,
  g.game_competitiveness_tier,
  g.is_home_team_winner,
  ht.team_abbr as home_team,
  vt.team_abbr as visitor_team,
  wt.team_abbr as winning_team
from main_marts.fct_game_results g
left join main_marts.dim_teams ht on g.home_team_key = ht.team_key
left join main_marts.dim_teams vt on g.visitor_team_key = vt.team_key
left join main_marts.dim_teams wt on g.winning_team_key = wt.team_key
order by g.game_date desc
