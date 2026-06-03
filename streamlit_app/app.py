import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
from streamlit_echarts import st_echarts
from pathlib import Path

st.set_page_config(page_title="NBA Analytics", page_icon="🏀", layout="wide")

DB_PATH = str(Path(__file__).resolve().parent.parent / "dbt_nba" / "reports" / "sources" / "nba" / "dbt_nba.duckdb")

if not Path(DB_PATH).exists():
    # Fallback: running from repo root
    DB_PATH = str(Path("dbt_nba") / "reports" / "sources" / "nba" / "dbt_nba.duckdb")


@st.cache_resource
def get_connection():
    return duckdb.connect(DB_PATH, read_only=True)


conn = get_connection()


@st.cache_data
def query(sql):
    return conn.execute(sql).df()


# --- Sidebar ---
st.sidebar.title("🏀 NBA Analytics")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Teams", "Players", "Shot Charts", "Head to Head", "Game Trends", "Quarter Analysis"],
)

# --- Helper: get seasons list ---
@st.cache_data
def get_seasons():
    return query("select season_start_year, season_display from main_marts.dim_seasons order by season_start_year desc")




# ============================================================
# PAGE: Overview
# ============================================================
if page == "Overview":
    st.title("🏀 NBA Analytics Dashboard")

    summary = query("""
        select count(*) as total_games,
               sum(case when is_overtime then 1 else 0 end) as overtime_games,
               round(avg(total_points), 1) as avg_total_points,
               round(avg(point_differential), 1) as avg_margin,
               min(game_date) as first_game,
               max(game_date) as last_game
        from main_marts.fct_game_results
    """)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Games", f"{summary['total_games'][0]:,}")
    c2.metric("Avg Points/Game", summary["avg_total_points"][0])
    c3.metric("OT Games", f"{summary['overtime_games'][0]:,}")
    c4.metric("Avg Margin", summary["avg_margin"][0])

    st.caption(f"Data from {summary['first_game'][0]} to {summary['last_game'][0]}")

    # Competitiveness breakdown
    col1, col2 = st.columns(2)
    with col1:
        comp = query("""
            select game_competitiveness_tier as tier, count(*) as games
            from main_marts.fct_game_results group by tier order by games desc
        """)
        fig = px.pie(comp, names="tier", values="games", title="Game Competitiveness Distribution")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        monthly = query("""
            select strftime(game_date, '%Y-%m') as month, count(*) as games,
                   round(avg(total_points), 1) as avg_pts
            from main_marts.fct_game_results
            where game_date >= current_date - interval '2 years'
            group by month order by month
        """)
        fig = px.bar(monthly, x="month", y="games", color="avg_pts",
                     color_continuous_scale="YlOrRd", title="Games per Month (Last 2 Years)")
        st.plotly_chart(fig, use_container_width=True)

    # Season-over-season scoring trend
    st.subheader("Scoring Trend by Season")
    season_trend = query("""
        select s.season_display, round(avg(g.total_points), 1) as avg_pts,
               round(avg(g.point_differential), 1) as avg_margin
        from main_marts.fct_game_results g
        join main_marts.dim_seasons s on g.season_key = s.season_key
        group by s.season_display, s.season_start_year
        order by s.season_start_year
    """)
    fig_trend = px.line(season_trend, x="season_display", y="avg_pts",
                        title="Average Total Points per Game by Season", markers=True)
    fig_trend.update_layout(xaxis_title="Season", yaxis_title="Avg Total Points")
    st.plotly_chart(fig_trend, use_container_width=True)

    st.subheader("Recent Games")

    # Calendar heatmap of game activity
    cal_data = query("""
        select game_date::varchar as day, count(*) as games
        from main_marts.fct_game_results
        where game_date >= (select max(game_date) - interval '18 months' from main_marts.fct_game_results)
        group by game_date order by game_date
    """)
    if not cal_data.empty:
        cal_list = [[row["day"], int(row["games"])] for _, row in cal_data.iterrows()]
        cal_option = {
            "tooltip": {"position": "top", "formatter": "{c0} games on {b0}"},
            "visualMap": {"min": 0, "max": 15, "calculable": True,
                          "orient": "horizontal", "left": "center", "top": "top"},
            "calendar": {"range": [cal_list[0][0][:7], cal_list[-1][0][:7]],
                         "cellSize": ["auto", 15]},
            "series": [{"type": "heatmap", "coordinateSystem": "calendar", "data": cal_list}],
        }
        st_echarts(options=cal_option, height="200px")

    games = query("""
        select g.game_date, ht.team_abbr as home, vt.team_abbr as away,
               g.home_points, g.visitor_points, wt.team_abbr as winner,
               g.point_differential as margin, g.game_competitiveness_tier as type
        from main_marts.fct_game_results g
        left join main_marts.dim_teams ht on g.home_team_key = ht.team_key
        left join main_marts.dim_teams vt on g.visitor_team_key = vt.team_key
        left join main_marts.dim_teams wt on g.winning_team_key = wt.team_key
        order by g.game_date desc limit 50
    """)
    st.dataframe(games, use_container_width=True)



# ============================================================
# PAGE: Teams
# ============================================================
elif page == "Teams":
    st.title("🏆 Team Analytics")

    seasons = get_seasons()
    selected_season = st.selectbox("Season", seasons["season_start_year"].tolist(),
                                   format_func=lambda x: seasons[seasons["season_start_year"]==x]["season_display"].values[0])

    ratings = query(f"""
        select team, count(*) as games,
               sum(case when game_result = 'W' then 1 else 0 end) as wins,
               sum(case when game_result = 'L' then 1 else 0 end) as losses,
               round(100.0 * sum(case when game_result = 'W' then 1 else 0 end) / count(*), 1) as win_pct,
               round(avg(offensive_rating), 1) as off_rtg,
               round(avg(defensive_rating), 1) as def_rtg,
               round(avg(net_rating), 1) as net_rtg,
               round(avg(pace), 1) as pace,
               round(avg(effective_fg_pct) * 100, 1) as efg_pct,
               round(avg(turnover_rate) * 100, 1) as tov_rate
        from main_intermediate.int_team_performance
        where season_start_year = {selected_season}
        group by team order by net_rtg desc
    """)

    # Net Rating chart
    fig = px.bar(ratings, x="net_rtg", y="team", orientation="h",
                 color="net_rtg", color_continuous_scale="RdYlGn",
                 title=f"Net Rating by Team ({seasons[seasons['season_start_year']==selected_season]['season_display'].values[0]})")
    fig.update_layout(yaxis=dict(autorange="reversed"), height=700)
    st.plotly_chart(fig, use_container_width=True)

    # Offense vs Defense scatter
    fig2 = px.scatter(ratings, x="off_rtg", y="def_rtg", text="team",
                      size="win_pct", color="net_rtg", color_continuous_scale="RdYlGn",
                      title="Offensive vs Defensive Rating (size = Win%)")
    fig2.update_traces(textposition="top center")
    fig2.update_layout(xaxis_title="Offensive Rating →", yaxis_title="← Defensive Rating (lower is better)",
                       yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig2, use_container_width=True)

    # Four Factors
    st.subheader("Four Factors")
    col1, col2 = st.columns(2)
    with col1:
        fig3 = px.bar(ratings.sort_values("efg_pct", ascending=False), x="efg_pct", y="team",
                      orientation="h", title="Effective FG%", color="efg_pct", color_continuous_scale="Greens")
        fig3.update_layout(yaxis=dict(autorange="reversed"), height=600, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)
    with col2:
        fig4 = px.bar(ratings.sort_values("tov_rate"), x="tov_rate", y="team",
                      orientation="h", title="Turnover Rate (lower = better)", color="tov_rate", color_continuous_scale="Reds_r")
        fig4.update_layout(yaxis=dict(autorange="reversed"), height=600, showlegend=False)
        st.plotly_chart(fig4, use_container_width=True)

    # Play style breakdown
    st.subheader("Team Styles")
    col1, col2 = st.columns(2)
    with col1:
        styles = query(f"""
            select shot_selection_style, count(*) as games,
                   round(avg(case when game_result = 'W' then 1.0 else 0.0 end) * 100, 1) as win_pct,
                   round(avg(offensive_rating), 1) as avg_off_rtg
            from main_intermediate.int_team_performance
            where season_start_year = {selected_season}
            group by shot_selection_style order by avg_off_rtg desc
        """)
        fig5 = px.bar(styles, x="shot_selection_style", y="win_pct",
                      color="avg_off_rtg", color_continuous_scale="RdYlGn",
                      title="Shot Selection Style Win%")
        st.plotly_chart(fig5, use_container_width=True)

    with col2:
        defense = query(f"""
            select defensive_activity, count(*) as games,
                   round(avg(case when game_result = 'W' then 1.0 else 0.0 end) * 100, 1) as win_pct,
                   round(avg(defensive_rating), 1) as avg_def_rtg
            from main_intermediate.int_team_performance
            where season_start_year = {selected_season}
            group by defensive_activity order by avg_def_rtg
        """)
        fig6 = px.bar(defense, x="defensive_activity", y="win_pct",
                      color="avg_def_rtg", color_continuous_scale="RdYlGn_r",
                      title="Defensive Activity Win% (color = Def Rtg, lower = better)")
        st.plotly_chart(fig6, use_container_width=True)

    # Win% gauges for top teams
    st.subheader("Top Team Win Rates")
    top_teams = ratings.nlargest(5, "win_pct")
    gauge_data = [
        {"value": float(row["win_pct"]), "name": row["team"],
         "title": {"offsetCenter": [f"{(i - 2) * 40}%", "70%"]},
         "detail": {"offsetCenter": [f"{(i - 2) * 40}%", "85%"]}}
        for i, (_, row) in enumerate(top_teams.iterrows())
    ]
    gauge_option = {
        "series": [{
            "type": "gauge",
            "startAngle": 90, "endAngle": -270,
            "pointer": {"show": False},
            "progress": {"show": True, "overlap": False, "roundCap": True, "clip": False},
            "axisLine": {"lineStyle": {"width": 30}},
            "splitLine": {"show": False},
            "axisTick": {"show": False},
            "axisLabel": {"show": False},
            "data": gauge_data,
            "title": {"fontSize": 12},
            "detail": {"width": 40, "height": 12, "fontSize": 12, "color": "inherit",
                       "borderColor": "inherit", "borderRadius": 20, "borderWidth": 1,
                       "formatter": "{value}%"},
        }]
    }
    st_echarts(options=gauge_option, height="300px")

    st.dataframe(ratings, use_container_width=True)



# ============================================================
# PAGE: Players
# ============================================================
elif page == "Players":
    st.title("👤 Player Analytics")

    seasons = get_seasons()
    selected_season = st.selectbox("Season", seasons["season_start_year"].tolist(),
                                   format_func=lambda x: seasons[seasons["season_start_year"]==x]["season_display"].values[0])
    min_games = st.slider("Minimum Games Played", 5, 60, 20)

    players = query(f"""
        select player_name, team, count(*) as games,
               round(avg(points), 1) as ppg,
               round(avg(assists), 1) as apg,
               round(avg(total_rebounds), 1) as rpg,
               round(avg(steals), 1) as spg,
               round(avg(blocks), 1) as bpg,
               round(avg(box_plus_minus), 2) as bpm,
               round(avg(usage_pct), 1) as usage,
               round(avg(true_shooting_pct) * 100, 1) as ts_pct,
               round(avg(net_rating), 1) as net_rtg,
               sum(case when is_double_double then 1 else 0 end) as double_doubles,
               sum(case when is_triple_double then 1 else 0 end) as triple_doubles,
               round(avg(three_pointers_made), 1) as threes_pg,
               round(avg(turnovers), 1) as tov_pg,
               round(avg(field_goals_made)::float / nullif(avg(field_goals_attempted), 0) * 100, 1) as fg_pct,
               round(avg(three_pointers_made)::float / nullif(avg(three_pointers_attempted), 0) * 100, 1) as three_pct
        from main_intermediate.int_player_performance
        where season_start_year = {selected_season} and minutes_played >= 20
        group by player_name, team
        having count(*) >= {min_games}
        order by bpm desc
    """)

    # Usage vs Efficiency scatter
    fig = px.scatter(players, x="usage", y="ts_pct", size="ppg",
                     hover_name="player_name", color="bpm",
                     color_continuous_scale="RdYlGn",
                     title="Usage Rate vs True Shooting % (size = PPG, color = BPM)")
    fig.update_layout(xaxis_title="Usage %", yaxis_title="True Shooting %", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Scoring vs Playmaking
    col1, col2 = st.columns(2)
    with col1:
        fig2 = px.scatter(players, x="ppg", y="apg", hover_name="player_name",
                          color="team", title="Scoring vs Playmaking", size="usage")
        st.plotly_chart(fig2, use_container_width=True)
    with col2:
        top_scorers = players.nlargest(20, "ppg")
        fig3 = px.bar(top_scorers, x="ppg", y="player_name", orientation="h",
                      color="ts_pct", color_continuous_scale="RdYlGn",
                      title="Top 20 Scorers (color = TS%)")
        fig3.update_layout(yaxis=dict(autorange="reversed"), height=500)
        st.plotly_chart(fig3, use_container_width=True)

    # Player comparison radar
    st.subheader("Player Comparison")
    player_list = players["player_name"].tolist()
    selected_players = st.multiselect("Select players to compare", player_list, default=player_list[:3])
    if selected_players:
        comp = players[players["player_name"].isin(selected_players)]
        categories = ["ppg", "apg", "rpg", "spg", "bpg", "usage", "ts_pct"]
        labels = ["PPG", "APG", "RPG", "SPG", "BPG", "USG%", "TS%"]
        # Normalize each category to 0-100 scale so radar fills evenly
        cat_min = players[categories].min()
        cat_max = players[categories].max()
        fig4 = go.Figure()
        for _, row in comp.iterrows():
            normalized = [
                100 * (row[c] - cat_min[c]) / (cat_max[c] - cat_min[c]) if cat_max[c] != cat_min[c] else 50
                for c in categories
            ]
            fig4.add_trace(go.Scatterpolar(
                r=normalized,
                theta=labels,
                fill="toself", name=row["player_name"]
            ))
        fig4.update_layout(title="Player Radar Comparison (normalized)", height=500,
                           polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
        st.plotly_chart(fig4, use_container_width=True)

        # ECharts radar with proper per-stat max indicators
        st.subheader("ECharts Radar (actual values)")
        radar_indicators = [
            {"name": "PPG", "max": float(players["ppg"].max() * 1.1)},
            {"name": "APG", "max": float(players["apg"].max() * 1.1)},
            {"name": "RPG", "max": float(players["rpg"].max() * 1.1)},
            {"name": "SPG", "max": float(players["spg"].max() * 1.1)},
            {"name": "BPG", "max": float(players["bpg"].max() * 1.1)},
            {"name": "USG%", "max": float(players["usage"].max() * 1.1)},
            {"name": "TS%", "max": float(players["ts_pct"].max() * 1.1)},
        ]
        radar_series_data = []
        for _, row in comp.iterrows():
            radar_series_data.append({
                "value": [float(row[c]) for c in categories],
                "name": row["player_name"],
            })
        echarts_radar_option = {
            "legend": {"data": [d["name"] for d in radar_series_data]},
            "radar": {"indicator": radar_indicators},
            "series": [{"type": "radar", "data": radar_series_data}],
        }
        st_echarts(options=echarts_radar_option, height="500px")

    # Parallel coordinates comparison
    st.subheader("Parallel Coordinates (multi-stat)")
    top_parallel = players.nlargest(15, "bpm")
    parallel_dims = ["ppg", "apg", "rpg", "usage", "ts_pct", "bpm", "net_rtg"]
    parallel_labels = ["PPG", "APG", "RPG", "USG%", "TS%", "BPM", "Net Rtg"]
    parallel_option = {
        "parallelAxis": [
            {"dim": i, "name": parallel_labels[i],
             "min": float(top_parallel[parallel_dims[i]].min()),
             "max": float(top_parallel[parallel_dims[i]].max())}
            for i in range(len(parallel_dims))
        ],
        "tooltip": {"trigger": "item"},
        "series": [{
            "type": "parallel",
            "lineStyle": {"width": 2, "opacity": 0.6},
            "data": [
                [float(row[c]) for c in parallel_dims]
                for _, row in top_parallel.iterrows()
            ],
        }],
    }
    st_echarts(options=parallel_option, height="400px")

    # Archetype breakdown
    st.subheader("Player Archetypes")
    archetypes = query(f"""
        select a.usage_tier, a.impact_tier, count(distinct pp.player_name) as players
        from main_intermediate.int_player_performance pp
        join main_marts.dim_player_game_archetypes a
            on pp.usage_tier = a.usage_tier
            and pp.impact_tier = a.impact_tier
            and pp.shooting_efficiency_tier = a.shooting_efficiency_tier
        where pp.season_start_year = {selected_season} and pp.minutes_played >= 20
            and a.usage_tier != 'Insufficient Minutes'
        group by a.usage_tier, a.impact_tier
        order by players desc
    """)
    if not archetypes.empty:
        fig_arch = px.treemap(archetypes, path=["usage_tier", "impact_tier"], values="players",
                              title="Player Archetype Distribution",
                              color="players", color_continuous_scale="Blues")
        st.plotly_chart(fig_arch, use_container_width=True)

    st.dataframe(players, use_container_width=True)



# ============================================================
# PAGE: Shot Charts
# ============================================================
elif page == "Shot Charts":
    st.title("🎯 Shot Analysis")

    seasons = get_seasons()
    selected_season = st.selectbox("Season", seasons["season_start_year"].tolist(),
                                   format_func=lambda x: seasons[seasons["season_start_year"]==x]["season_display"].values[0])

    # Player shot chart (spatial)
    st.subheader("Player Shot Chart")
    top_shooters = query(f"""
        select p.player_name, count(*) as shots
        from main_marts.fct_player_shots s
        join main_marts.dim_players p on s.player_key = p.player_key
        join main_marts.dim_seasons sea on s.season_key = sea.season_key
        where sea.season_start_year = {selected_season} and s.shot_source = 'shot_chart'
        group by p.player_name having count(*) >= 50
        order by shots desc
    """)
    if not top_shooters.empty:
        selected_player = st.selectbox("Player", top_shooters["player_name"].tolist())
        shot_data = query(f"""
            select s.shot_x_coordinate as x, s.shot_y_coordinate as y,
                   s.is_made, s.shot_distance_zone, s.distance_ft
            from main_marts.fct_player_shots s
            join main_marts.dim_players p on s.player_key = p.player_key
            join main_marts.dim_seasons sea on s.season_key = sea.season_key
            where sea.season_start_year = {selected_season}
                and s.shot_source = 'shot_chart'
                and p.player_name = '{selected_player}'
        """)
        if not shot_data.empty:
            shot_data["result"] = shot_data["is_made"].map({True: "Made", False: "Missed"})
            fig_court = px.scatter(
                shot_data, x="x", y="y", color="result",
                color_discrete_map={"Made": "#22c55e", "Missed": "#dc2626"},
                opacity=0.5, title=f"{selected_player} Shot Chart",
                hover_data=["shot_distance_zone", "distance_ft"]
            )
            fig_court.update_layout(
                height=550, width=600,
                xaxis=dict(showgrid=False, zeroline=False, range=[-30, 500], showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, range=[-10, 470], scaleanchor="x", showticklabels=False),
                plot_bgcolor="rgba(0,0,0,0)"
            )
            fig_court.update_traces(marker=dict(size=4))
            st.plotly_chart(fig_court, use_container_width=True)

    # Shot zone breakdown
    st.subheader("League Shot Zone Breakdown")
    zone_data = query(f"""
        select sz.shot_distance_zone, sz.zone_group, sz.zone_category, sz.zone_order,
               count(*) as attempts, sum(s.is_made::int) as makes,
               round(100.0 * sum(s.is_made::int) / count(*), 1) as fg_pct,
               round(avg(s.shot_point_value), 2) as avg_value
        from main_marts.fct_player_shots s
        join main_marts.dim_shot_zones sz on s.shot_distance_zone = sz.shot_distance_zone
        join main_marts.dim_seasons sea on s.season_key = sea.season_key
        where sea.season_start_year = {selected_season}
        group by sz.shot_distance_zone, sz.zone_group, sz.zone_category, sz.zone_order
        order by sz.zone_order
    """)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(zone_data, x="shot_distance_zone", y="attempts", color="fg_pct",
                     color_continuous_scale="RdYlGn", title="Shot Attempts by Zone")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(zone_data, x="shot_distance_zone", y="fg_pct", color="zone_group",
                      title="FG% by Shot Zone")
        st.plotly_chart(fig2, use_container_width=True)

    # Clutch shooting
    st.subheader("Clutch Shooting Leaders")
    clutch = query(f"""
        select p.player_name,
               count(*) as clutch_attempts,
               sum(s.is_made::int) as clutch_makes,
               round(100.0 * sum(s.is_made::int) / count(*), 1) as clutch_pct
        from main_marts.fct_player_shots s
        join main_marts.dim_players p on s.player_key = p.player_key
        join main_marts.dim_seasons sea on s.season_key = sea.season_key
        where s.is_clutch_shot and sea.season_start_year = {selected_season}
        group by p.player_name
        having count(*) >= 20
        order by clutch_makes desc limit 25
    """)
    fig3 = px.scatter(clutch, x="clutch_attempts", y="clutch_pct", size="clutch_makes",
                      hover_name="player_name", title="Clutch Shooting: Volume vs Accuracy",
                      color="clutch_pct", color_continuous_scale="RdYlGn")
    st.plotly_chart(fig3, use_container_width=True)

    # Shot profile types
    st.subheader("Shot Profile Distribution")
    profiles = query(f"""
        select shot_profile_type, count(*) as player_games,
               round(avg(true_shooting_pct) * 100, 1) as avg_ts,
               round(avg(total_points), 1) as avg_pts
        from main_marts.fct_player_game_shooting s
        join main_marts.dim_seasons sea on s.season_key = sea.season_key
        where sea.season_start_year = {selected_season}
        group by shot_profile_type order by player_games desc
    """)
    fig4 = px.treemap(profiles, path=["shot_profile_type"], values="player_games",
                      color="avg_ts", color_continuous_scale="RdYlGn",
                      title="Shot Profile Types (size = frequency, color = TS%)")
    st.plotly_chart(fig4, use_container_width=True)



# ============================================================
# PAGE: Head to Head
# ============================================================
elif page == "Head to Head":
    st.title("⚔️ Head-to-Head Matchups")

    teams = query("select distinct team from main_intermediate.int_team_performance order by team")
    team_list = teams["team"].tolist()

    col1, col2 = st.columns(2)
    with col1:
        team_a = st.selectbox("Team A", team_list, index=0)
    with col2:
        team_b = st.selectbox("Team B", team_list, index=min(1, len(team_list)-1))

    if team_a and team_b and team_a != team_b:
        h2h = query(f"""
            select game_date, team, opponent_team, points, game_result,
                   offensive_rating, defensive_rating, net_rating, pace
            from main_intermediate.int_team_performance
            where team = '{team_a}' and opponent_team = '{team_b}'
            order by game_date desc limit 20
        """)

        if not h2h.empty:
            wins_a = (h2h["game_result"] == "W").sum()
            wins_b = len(h2h) - wins_a

            c1, c2, c3 = st.columns(3)
            c1.metric(f"{team_a} Wins", wins_a)
            c2.metric("Games Played", len(h2h))
            c3.metric(f"{team_b} Wins", wins_b)

            fig = px.bar(h2h, x="game_date", y="points", color="game_result",
                         title=f"{team_a} Points vs {team_b} (Last 20 Meetings)",
                         color_discrete_map={"W": "#22c55e", "L": "#dc2626"})
            st.plotly_chart(fig, use_container_width=True)

            # Rating comparison
            st.subheader("Average Ratings in Matchup")
            avg_stats = h2h[["offensive_rating", "defensive_rating", "net_rating", "pace"]].mean()
            st.dataframe(avg_stats.to_frame("Average").T, use_container_width=True)
            st.dataframe(h2h, use_container_width=True)
        else:
            st.info("No head-to-head games found between these teams.")
    else:
        st.info("Select two different teams to compare.")



# ============================================================
# PAGE: Game Trends
# ============================================================
elif page == "Game Trends":
    st.title("📈 League Trends Over Time")

    # Pace & Scoring using season_display
    pace = query("""
        select s.season_display as season, s.season_start_year,
               round(avg(g.matchup_pace), 1) as avg_pace,
               round(avg(g.total_points), 1) as avg_points,
               round(avg(g.home_effective_fg_pct + g.visitor_effective_fg_pct) / 2 * 100, 1) as avg_efg_pct
        from main_intermediate.int_games_enriched g
        join main_marts.dim_seasons s on g.season_start_year = s.season_start_year
        group by s.season_display, s.season_start_year
        order by s.season_start_year
    """)

    fig = px.line(pace, x="season", y="avg_points", title="Scoring Evolution",
                  markers=True)
    fig.add_scatter(x=pace["season"], y=pace["avg_pace"], name="Pace", yaxis="y2")
    fig.update_layout(yaxis2=dict(title="Pace", overlaying="y", side="right"),
                      yaxis_title="Avg Points/Game")
    st.plotly_chart(fig, use_container_width=True)

    # Efficiency trend
    fig_eff = px.area(pace, x="season", y="avg_efg_pct",
                      title="League-Wide Effective FG% Trend")
    st.plotly_chart(fig_eff, use_container_width=True)

    # Game Drama
    drama = query("""
        select s.season_display as season, s.season_start_year,
               round(100.0 * sum(case when g.is_overtime then 1 else 0 end) / count(*), 1) as ot_pct,
               round(100.0 * sum(case when g.point_differential <= 5 then 1 else 0 end) / count(*), 1) as clutch_pct,
               round(100.0 * sum(case when g.point_differential >= 20 then 1 else 0 end) / count(*), 1) as blowout_pct
        from main_intermediate.int_games_enriched g
        join main_marts.dim_seasons s on g.season_start_year = s.season_start_year
        group by s.season_display, s.season_start_year
        order by s.season_start_year
    """)

    fig2 = px.area(drama, x="season", y=["clutch_pct", "blowout_pct", "ot_pct"],
                   title="Game Drama: Clutch (≤5pt) vs Blowouts (20+) vs OT")
    st.plotly_chart(fig2, use_container_width=True)

    # Home court advantage
    home = query("""
        select s.season_display as season,
               round(100.0 * sum(case when g.is_home_team_winner then 1 else 0 end) / count(*), 1) as home_win_pct
        from main_marts.fct_game_results g
        join main_marts.dim_seasons s on g.season_key = s.season_key
        group by s.season_display, s.season_start_year
        order by s.season_start_year
    """)

    fig3 = px.line(home, x="season", y="home_win_pct",
                   title="Home Court Advantage Over Time", markers=True)
    fig3.update_layout(yaxis_range=[40, 70])
    fig3.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50%")
    st.plotly_chart(fig3, use_container_width=True)

    # Points distribution
    st.subheader("Scoring Distribution")
    pts_dist = query("""
        select total_points from main_marts.fct_game_results
    """)
    fig4 = px.histogram(pts_dist, x="total_points", nbins=50,
                        title="Distribution of Total Points Scored per Game",
                        color_discrete_sequence=["#3b82f6"])
    fig4.update_layout(xaxis_title="Total Points", yaxis_title="Games")
    st.plotly_chart(fig4, use_container_width=True)



# ============================================================
# PAGE: Quarter Analysis
# ============================================================
elif page == "Quarter Analysis":
    st.title("⏱️ Quarter-by-Quarter Analysis")

    seasons = get_seasons()
    selected_season = st.selectbox("Season", seasons["season_start_year"].tolist(),
                                   format_func=lambda x: seasons[seasons["season_start_year"]==x]["season_display"].values[0])

    # Scoring by quarter
    quarter_avg = query(f"""
        select q.period,
               round(avg(q.points_scored), 1) as avg_pts,
               round(avg(q.period_point_differential), 2) as avg_diff
        from main_marts.fct_quarter_scoring q
        join main_marts.dim_seasons s on q.season_key = s.season_key
        where s.season_start_year = {selected_season} and q.period in ('Q1','Q2','Q3','Q4')
        group by q.period order by q.period
    """)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(quarter_avg, x="period", y="avg_pts",
                     title="Average Points Scored per Quarter",
                     color="avg_pts", color_continuous_scale="Blues",
                     labels={"period": "Quarter", "avg_pts": "Avg Points"})
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(quarter_avg, x="period", y="avg_diff",
                      title="Avg Point Differential by Quarter",
                      color="avg_diff", color_continuous_scale="RdYlGn",
                      labels={"period": "Quarter", "avg_diff": "Avg Differential"})
        st.plotly_chart(fig2, use_container_width=True)

    # Best Q1/Q4 teams
    st.subheader("Best Teams by Quarter")
    quarter_sel = st.radio("Quarter", ["Q1", "Q2", "Q3", "Q4"], horizontal=True)

    team_quarter = query(f"""
        select t.team_abbr as team,
               round(avg(q.points_scored), 1) as avg_pts,
               round(avg(q.period_point_differential), 2) as avg_diff,
               count(*) as games
        from main_marts.fct_quarter_scoring q
        join main_marts.dim_teams t on q.team_key = t.team_key
        join main_marts.dim_seasons s on q.season_key = s.season_key
        where s.season_start_year = {selected_season} and q.period = '{quarter_sel}'
        group by t.team_abbr
        having count(*) >= 10
        order by avg_pts desc
    """)

    fig3 = px.bar(team_quarter, x="avg_pts", y="team", orientation="h",
                  color="avg_diff", color_continuous_scale="RdYlGn",
                  title=f"{quarter_sel} Scoring Leaders (color = point diff)")
    fig3.update_layout(yaxis=dict(autorange="reversed"), height=600)
    st.plotly_chart(fig3, use_container_width=True)

    # Comeback analysis
    st.subheader("Comeback Games")
    comebacks = query(f"""
        with q3_trailing as (
            select q.game_id, q.team_key,
                   sum(q.period_point_differential) as through_q3_diff
            from main_marts.fct_quarter_scoring q
            join main_marts.dim_seasons s on q.season_key = s.season_key
            where s.season_start_year = {selected_season} and q.period in ('Q1','Q2','Q3')
            group by q.game_id, q.team_key
            having sum(q.period_point_differential) < -10
        ),
        q4_results as (
            select q.game_id, q.team_key, q.points_scored as q4_pts,
                   q.period_point_differential as q4_diff
            from main_marts.fct_quarter_scoring q
            join main_marts.dim_seasons s on q.season_key = s.season_key
            where s.season_start_year = {selected_season} and q.period = 'Q4'
        )
        select t.team_abbr as team,
               count(*) as times_trailing_10_after_q3,
               sum(case when c.through_q3_diff + r.q4_diff > 0 then 1 else 0 end) as comebacks,
               round(100.0 * sum(case when c.through_q3_diff + r.q4_diff > 0 then 1 else 0 end) / count(*), 1) as comeback_pct
        from q3_trailing c
        join q4_results r on c.game_id = r.game_id and c.team_key = r.team_key
        join main_marts.dim_teams t on c.team_key = t.team_key
        group by t.team_abbr
        having count(*) >= 3
        order by comeback_pct desc
    """)

    if not comebacks.empty:
        fig4 = px.bar(comebacks, x="team", y="comeback_pct",
                      color="comebacks", title="Comeback Rate (Down 10+ After Q3)",
                      labels={"comeback_pct": "Comeback %"})
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(comebacks, use_container_width=True)
    else:
        st.info("No comeback data available for this season.")
