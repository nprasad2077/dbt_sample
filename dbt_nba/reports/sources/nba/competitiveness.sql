select
  game_competitiveness_tier,
  count(*) as games
from main_marts.fct_game_results
group by game_competitiveness_tier
order by games desc
