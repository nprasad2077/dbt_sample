select
  season_start_year || '-' || substr(cast(season_start_year + 1 as varchar), 3, 2) as season,
  round(100.0 * sum(case when is_overtime then 1 else 0 end) / count(*), 1) as ot_pct,
  round(100.0 * sum(case when point_differential <= 5 then 1 else 0 end) / count(*), 1) as clutch_pct,
  round(100.0 * sum(case when point_differential >= 20 then 1 else 0 end) / count(*), 1) as blowout_pct
from main_intermediate.int_games_enriched
group by season_start_year
order by season_start_year
