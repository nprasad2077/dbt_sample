---
title: NBA Analytics Dashboard
---

```sql games
select * from nba.games
```

```sql season_summary
select * from nba.season_summary
```

```sql competitiveness
select * from nba.competitiveness
```

```sql home_advantage
select * from nba.home_advantage
```

```sql top_scorers
select * from nba.top_scorers
```

```sql pace_and_scoring
select * from nba.pace_and_scoring
```

```sql team_ratings
select * from nba.team_ratings
```

```sql play_styles
select * from nba.play_styles
```

```sql player_impact
select * from nba.player_impact
```

```sql game_drama
select * from nba.game_drama
```

```sql usage_efficiency
select * from nba.usage_efficiency
```

# 🏀 NBA Analytics

<BigValue data={season_summary} value=total_games title="Total Games" />
<BigValue data={season_summary} value=avg_total_points title="Avg Points/Game" />
<BigValue data={season_summary} value=overtime_games title="OT Games" />
<BigValue data={season_summary} value=avg_margin title="Avg Margin" />

---

## League Evolution: Pace & Scoring

<LineChart
  data={pace_and_scoring}
  x=season
  y={['avg_total_points', 'avg_pace']}
  y2=avg_efg_pct
  title="How the NBA Has Changed: Points, Pace & Efficiency"
  yAxisTitle="Points / Pace"
  y2AxisTitle="eFG%"
/>

## Game Drama Over Time

<AreaChart
  data={game_drama}
  x=season
  y={['clutch_pct', 'blowout_pct', 'ot_pct']}
  title="% of Games: Clutch (≤5pt margin) vs Blowouts (20+) vs Overtime"
  yAxisTitle="% of Games"
/>

---

## Current Season: Team Power Rankings

<BarChart
  data={team_ratings}
  x=team
  y=avg_net_rating
  title="Net Rating by Team (Current Season)"
  swapXY=true
  colorPalette={['#dc2626', '#dc2626', '#dc2626', '#dc2626', '#dc2626', '#f97316', '#f97316', '#f97316', '#f97316', '#f97316', '#6b7280', '#6b7280', '#6b7280', '#6b7280', '#6b7280', '#6b7280', '#6b7280', '#6b7280', '#6b7280', '#6b7280', '#22c55e', '#22c55e', '#22c55e', '#22c55e', '#22c55e', '#16a34a', '#16a34a', '#16a34a', '#16a34a', '#16a34a']}
/>

<DataTable data={team_ratings} rows=30>
  <Column id=team title="Team" />
  <Column id=wins title="W" />
  <Column id=games title="GP" />
  <Column id=win_pct title="Win%" />
  <Column id=avg_off_rating title="ORtg" />
  <Column id=avg_def_rating title="DRtg" />
  <Column id=avg_net_rating title="Net" contentType=colorscale colorScale=RdYlGn />
  <Column id=avg_pace title="Pace" />
</DataTable>

## Shot Selection Style & Winning

<BarChart
  data={play_styles}
  x=shot_selection_style
  y={['win_pct', 'avg_off_rating']}
  y2=avg_off_rating
  title="Does Three-Point Shooting Win Games?"
  yAxisTitle="Win %"
  y2AxisTitle="Off Rating"
/>

---

## Player Impact: Usage vs Efficiency

<ScatterPlot
  data={usage_efficiency}
  x=usage
  y=efficiency
  size=ppg
  tooltipTitle=player_name
  title="Usage Rate vs True Shooting % (bubble size = PPG)"
  xAxisTitle="Usage Rate %"
  yAxisTitle="True Shooting %"
/>

## Top 30 Players by Box Plus/Minus (Current Season)

<DataTable data={player_impact} rows=30>
  <Column id=player_name title="Player" />
  <Column id=team title="Team" />
  <Column id=games title="GP" />
  <Column id=ppg title="PPG" />
  <Column id=apg title="APG" />
  <Column id=rpg title="RPG" />
  <Column id=avg_bpm title="BPM" contentType=colorscale colorScale=RdYlGn />
  <Column id=avg_usage title="USG%" />
  <Column id=ts_pct title="TS%" />
  <Column id=double_doubles title="DD" />
  <Column id=triple_doubles title="TD" />
</DataTable>

<BarChart
  data={player_impact}
  x=player_name
  y=avg_bpm
  title="Box Plus/Minus Leaders"
  swapXY=true
/>

---

## Home Court Advantage Trend

<LineChart
  data={home_advantage}
  x=season_display
  y=home_win_pct
  title="Home Team Win % by Season"
  yAxisTitle="Win %"
  yMin=40
  yMax=70
  markers=true
/>

## Recent Games

<DataTable data={games} rows=20>
  <Column id=game_date title="Date" />
  <Column id=home_team title="Home" />
  <Column id=visitor_team title="Away" />
  <Column id=home_points title="H Pts" />
  <Column id=visitor_points title="A Pts" />
  <Column id=winning_team title="Winner" />
  <Column id=point_differential title="Margin" />
  <Column id=game_competitiveness_tier title="Type" />
  <Column id=is_overtime title="OT" />
</DataTable>
