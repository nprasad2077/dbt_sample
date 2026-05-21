select
  season_start_year || '-' || substr(cast(season_start_year + 1 as varchar), 3, 2) as season,
  round(avg(matchup_pace), 1) as avg_pace,
  round(avg(total_points), 1) as avg_total_points,
  round(avg(home_effective_fg_pct + visitor_effective_fg_pct) / 2 * 100, 1) as avg_efg_pct,
  round(avg(point_differential), 1) as avg_margin,
  count(*) as games
from main_intermediate.int_games_enriched
group by season_start_year
order by season_start_year
