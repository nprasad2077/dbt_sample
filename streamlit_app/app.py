import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_echarts import st_echarts
from pathlib import Path

st.set_page_config(page_title="NBA Analytics", page_icon="🏀", layout="wide")

# ============================================================
# CONNECTION & QUERY INFRASTRUCTURE
# ============================================================

DB_PATH = str(Path(__file__).resolve().parent.parent / "dbt_nba" / "reports" / "sources" / "nba" / "dbt_nba.duckdb")

if not Path(DB_PATH).exists():
    DB_PATH = str(Path("dbt_nba") / "reports" / "sources" / "nba" / "dbt_nba.duckdb")


@st.cache_resource
def get_connection():
    """Persistent read-only DuckDB connection."""
    return duckdb.connect(DB_PATH, read_only=True)


@st.cache_data(ttl=3600)
def query(sql: str, params: list = None) -> pd.DataFrame:
    """Execute SQL (optionally parameterized) and return cached DataFrame."""
    conn = get_connection()
    if params:
        return conn.execute(sql, params).df()
    return conn.execute(sql).df()


@st.cache_data(ttl=3600)
def get_seasons() -> pd.DataFrame:
    return query("SELECT season_start_year, season_display FROM main_marts.dim_seasons ORDER BY season_start_year DESC")


# ============================================================
# GLOBAL STATE & SIDEBAR
# ============================================================

seasons = get_seasons()
season_options = seasons["season_start_year"].tolist()
season_labels = dict(zip(seasons["season_start_year"], seasons["season_display"]))

if "season" not in st.session_state:
    st.session_state["season"] = season_options[0]

st.sidebar.title("🏀 NBA Analytics")

st.session_state["season"] = st.sidebar.selectbox(
    "Season",
    season_options,
    index=season_options.index(st.session_state["season"]),
    format_func=lambda x: season_labels[x],
)

st.sidebar.divider()

page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Teams", "Player Lab", "Shot Charts", "Head to Head", "Game Trends", "Quarter Analysis"],
)

# Convenience accessors
SEASON = st.session_state["season"]
SEASON_LABEL = season_labels[SEASON]




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
        st.plotly_chart(fig, width="stretch")

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
        st.plotly_chart(fig, width="stretch")

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
    st.plotly_chart(fig_trend, width="stretch")

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
    st.dataframe(games, width="stretch")



# ============================================================
# PAGE: Teams
# ============================================================
elif page == "Teams":
    st.title(f"🏆 Team Analytics — {SEASON_LABEL}")

    selected_season = SEASON

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
                 title=f"Net Rating by Team ({SEASON_LABEL})")
    fig.update_layout(yaxis=dict(autorange="reversed"), height=700)
    st.plotly_chart(fig, width="stretch")

    # Offense vs Defense scatter
    fig2 = px.scatter(ratings, x="off_rtg", y="def_rtg", text="team",
                      size="win_pct", color="net_rtg", color_continuous_scale="RdYlGn",
                      title="Offensive vs Defensive Rating (size = Win%)")
    fig2.update_traces(textposition="top center")
    fig2.update_layout(xaxis_title="Offensive Rating →", yaxis_title="← Defensive Rating (lower is better)",
                       yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig2, width="stretch")

    # Four Factors
    st.subheader("Four Factors")
    col1, col2 = st.columns(2)
    with col1:
        fig3 = px.bar(ratings.sort_values("efg_pct", ascending=False), x="efg_pct", y="team",
                      orientation="h", title="Effective FG%", color="efg_pct", color_continuous_scale="Greens")
        fig3.update_layout(yaxis=dict(autorange="reversed"), height=600, showlegend=False)
        st.plotly_chart(fig3, width="stretch")
    with col2:
        fig4 = px.bar(ratings.sort_values("tov_rate"), x="tov_rate", y="team",
                      orientation="h", title="Turnover Rate (lower = better)", color="tov_rate", color_continuous_scale="Reds_r")
        fig4.update_layout(yaxis=dict(autorange="reversed"), height=600, showlegend=False)
        st.plotly_chart(fig4, width="stretch")

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
        st.plotly_chart(fig5, width="stretch")

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
        st.plotly_chart(fig6, width="stretch")

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

    st.dataframe(ratings, width="stretch")



# ============================================================
# PAGE: Player Lab
# ============================================================
elif page == "Player Lab":
    st.title(f"👤 Player Lab — {SEASON_LABEL}")

    min_games = st.sidebar.slider("Min Games", 5, 60, 20, key="player_min_games")

    # --- Core player data ---
    players = query("""
        SELECT player_name, team, count(*) AS games,
               round(avg(points), 1) AS ppg,
               round(avg(assists), 1) AS apg,
               round(avg(total_rebounds), 1) AS rpg,
               round(avg(steals), 1) AS spg,
               round(avg(blocks), 1) AS bpg,
               round(avg(box_plus_minus), 2) AS bpm,
               round(avg(usage_pct), 1) AS usage,
               round(avg(true_shooting_pct) * 100, 1) AS ts_pct,
               round(avg(net_rating), 1) AS net_rtg,
               sum(CASE WHEN is_double_double THEN 1 ELSE 0 END) AS double_doubles,
               sum(CASE WHEN is_triple_double THEN 1 ELSE 0 END) AS triple_doubles
        FROM main_intermediate.int_player_performance
        WHERE season_start_year = ? AND minutes_played >= 20
        GROUP BY player_name, team
        HAVING count(*) >= ?
        ORDER BY bpm DESC
    """, [SEASON, min_games])

    tab_board, tab_compare, tab_archetypes = st.tabs(
        ["📊 Leaderboard", "🔀 Comparison", "🧬 Archetypes"]
    )

    # --- TAB: Leaderboard ---
    with tab_board:
        # Usage vs Efficiency quadrant scatter
        fig = px.scatter(
            players, x="usage", y="ts_pct", size="ppg",
            hover_name="player_name", color="bpm",
            color_continuous_scale="RdYlGn",
            title="Usage vs True Shooting % (size = PPG, color = BPM)",
        )
        fig.update_layout(height=500, xaxis_title="Usage %", yaxis_title="True Shooting %")
        # Quadrant lines at median
        fig.add_hline(y=players["ts_pct"].median(), line_dash="dot", line_color="gray", opacity=0.4)
        fig.add_vline(x=players["usage"].median(), line_dash="dot", line_color="gray", opacity=0.4)
        st.plotly_chart(fig, width="stretch")

        # Scoring vs Playmaking + Top Scorers side by side
        col1, col2 = st.columns(2)
        with col1:
            fig2 = px.scatter(players, x="ppg", y="apg", hover_name="player_name",
                              color="bpm", color_continuous_scale="RdYlGn",
                              size="usage", title="Scoring vs Playmaking")
            st.plotly_chart(fig2, width="stretch")
        with col2:
            top_scorers = players.nlargest(15, "ppg")
            fig3 = px.bar(top_scorers, x="ppg", y="player_name", orientation="h",
                          color="ts_pct", color_continuous_scale="RdYlGn",
                          title="Top 15 Scorers (color = TS%)")
            fig3.update_layout(yaxis=dict(autorange="reversed"), height=450)
            st.plotly_chart(fig3, width="stretch")

        # Enhanced leaderboard table
        st.dataframe(
            players,
            column_config={
                "ts_pct": st.column_config.ProgressColumn(
                    "TS%", min_value=40, max_value=75, format="%.1f%%"
                ),
                "usage": st.column_config.ProgressColumn(
                    "USG%", min_value=5, max_value=40, format="%.1f%%"
                ),
                "bpm": st.column_config.NumberColumn("BPM", format="%.2f"),
            },
            width="stretch",
            hide_index=True,
        )

    # --- TAB: Comparison ---
    with tab_compare:
        player_list = players["player_name"].tolist()
        selected_players = st.multiselect(
            "Select players to compare", player_list, default=player_list[:3]
        )
        if selected_players:
            comp = players[players["player_name"].isin(selected_players)]
            categories = ["ppg", "apg", "rpg", "spg", "bpg", "usage", "ts_pct"]
            labels = ["PPG", "APG", "RPG", "SPG", "BPG", "USG%", "TS%"]

            # ECharts radar — actual values with per-stat max
            # Distinct color palette to avoid similar blues
            RADAR_COLORS = [
                "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
                "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
            ]
            radar_indicators = [
                {"name": labels[i], "max": float(players[c].max() * 1.15)}
                for i, c in enumerate(categories)
            ]
            radar_data = [
                {
                    "value": [float(row[c]) for c in categories],
                    "name": row["player_name"],
                    "lineStyle": {"color": RADAR_COLORS[i % len(RADAR_COLORS)], "width": 2.5},
                    "areaStyle": {"color": RADAR_COLORS[i % len(RADAR_COLORS)], "opacity": 0.3},
                    "itemStyle": {"color": RADAR_COLORS[i % len(RADAR_COLORS)]},
                }
                for i, (_, row) in enumerate(comp.iterrows())
            ]
            echarts_option = {
                "legend": {"data": [d["name"] for d in radar_data], "top": "bottom"},
                "color": RADAR_COLORS[:len(radar_data)],
                "radar": {
                    "indicator": radar_indicators,
                    "shape": "polygon",
                    "splitArea": {"areaStyle": {"color": ["#1a1a2e", "#16213e", "#0f3460", "#1a1a2e", "#16213e"]}},
                    "axisLine": {"lineStyle": {"color": "rgba(200, 200, 200, 0.3)"}},
                    "splitLine": {"lineStyle": {"color": "rgba(200, 200, 200, 0.2)"}},
                },
                "series": [{"type": "radar", "data": radar_data}],
            }
            st_echarts(options=echarts_option, height="500px")

            # Side-by-side stat table
            st.dataframe(
                comp.set_index("player_name")[categories + ["bpm", "net_rtg", "games"]].rename(
                    columns=dict(zip(categories, labels))
                ),
                width="stretch",
            )

            # Parallel coordinates for top 15 by BPM
            st.subheader("Parallel Coordinates (Top 15 BPM)")
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

    # --- TAB: Archetypes ---
    with tab_archetypes:
        # Modal archetype per player (most frequent tier combo) — with player detail
        archetype_players = query("""
            WITH player_archetype_counts AS (
                SELECT player_name, team, usage_tier, impact_tier, shooting_efficiency_tier,
                       count(*) AS games_in_archetype
                FROM main_intermediate.int_player_performance
                WHERE season_start_year = ? AND minutes_played >= 20
                      AND usage_tier != 'Insufficient Minutes'
                GROUP BY player_name, team, usage_tier, impact_tier, shooting_efficiency_tier
            ),
            player_modal AS (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY player_name, team ORDER BY games_in_archetype DESC
                ) AS rn
                FROM player_archetype_counts
            )
            SELECT player_name, team, usage_tier, impact_tier, shooting_efficiency_tier,
                   games_in_archetype
            FROM player_modal
            WHERE rn = 1
        """, [SEASON])

        if not archetype_players.empty:
            # Aggregate for sunburst
            archetypes = (
                archetype_players.groupby(["usage_tier", "impact_tier", "shooting_efficiency_tier"])
                .agg(players=("player_name", "count"))
                .reset_index()
                .query("players >= 2")
                .sort_values("players", ascending=False)
            )

            fig_arch = px.sunburst(
                archetypes,
                path=["usage_tier", "impact_tier", "shooting_efficiency_tier"],
                values="players",
                title="Player Archetype Hierarchy (click segments, then filter below)",
                color="players", color_continuous_scale="Blues",
            )
            fig_arch.update_layout(height=600)
            st.plotly_chart(fig_arch, width="stretch")

            # Drill-down selectors
            st.subheader("🔍 Drill Into Archetype")
            usage_tiers = ["All"] + sorted(archetype_players["usage_tier"].unique().tolist())
            sel_usage = st.selectbox("Usage Tier", usage_tiers, key="arch_usage")

            filtered = archetype_players
            if sel_usage != "All":
                filtered = filtered[filtered["usage_tier"] == sel_usage]

            impact_tiers = ["All"] + sorted(filtered["impact_tier"].unique().tolist())
            sel_impact = st.selectbox("Impact Tier", impact_tiers, key="arch_impact")

            if sel_impact != "All":
                filtered = filtered[filtered["impact_tier"] == sel_impact]

            eff_tiers = ["All"] + sorted(filtered["shooting_efficiency_tier"].unique().tolist())
            sel_eff = st.selectbox("Shooting Efficiency Tier", eff_tiers, key="arch_eff")

            if sel_eff != "All":
                filtered = filtered[filtered["shooting_efficiency_tier"] == sel_eff]

            # Show filtered player table with stats
            st.caption(f"Showing {len(filtered)} players matching selection")
            st.dataframe(
                filtered[["player_name", "team", "usage_tier", "impact_tier",
                          "shooting_efficiency_tier", "games_in_archetype"]]
                .sort_values("games_in_archetype", ascending=False)
                .reset_index(drop=True),
                width="stretch", hide_index=True,
            )

        # Specialist flags breakdown — percentage-based threshold (25%)
        st.subheader("Player Specialists")
        specialists = query("""
            SELECT player_name, team, count(*) AS games,
                   round(avg(points), 1) AS ppg,
                   round(avg(box_plus_minus), 2) AS bpm,
                   round(100.0 * sum(CASE WHEN is_versatile THEN 1 ELSE 0 END) / count(*), 1) AS pct_versatile,
                   round(100.0 * sum(CASE WHEN is_defensive_specialist THEN 1 ELSE 0 END) / count(*), 1) AS pct_def_spec,
                   round(100.0 * sum(CASE WHEN is_three_and_d THEN 1 ELSE 0 END) / count(*), 1) AS pct_three_and_d
            FROM main_intermediate.int_player_performance
            WHERE season_start_year = ? AND minutes_played >= 20
            GROUP BY player_name, team
            HAVING count(*) >= ?
        """, [SEASON, min_games])

        col1, col2, col3 = st.columns(3)
        with col1:
            versatile = specialists[specialists["pct_versatile"] >= 25].sort_values("pct_versatile", ascending=False)
            st.metric("🎯 Versatile", len(versatile))
            st.caption("≥25% of games with double-double stats")
            st.dataframe(
                versatile[["player_name", "team", "ppg", "pct_versatile"]],
                hide_index=True, width="stretch",
            )
        with col2:
            def_spec = specialists[specialists["pct_def_spec"] >= 25].sort_values("pct_def_spec", ascending=False)
            st.metric("🛡️ Defensive Specialists", len(def_spec))
            st.caption("≥25% of games as defensive specialist")
            st.dataframe(
                def_spec[["player_name", "team", "ppg", "pct_def_spec"]],
                hide_index=True, width="stretch",
            )
        with col3:
            three_d = specialists[specialists["pct_three_and_d"] >= 25].sort_values("pct_three_and_d", ascending=False)
            st.metric("🏹 Three-and-D", len(three_d))
            st.caption("≥25% of games as 3-and-D player")
            st.dataframe(
                three_d[["player_name", "team", "ppg", "pct_three_and_d"]],
                hide_index=True, width="stretch",
            )



# ============================================================
# PAGE: Shot Charts
# ============================================================
elif page == "Shot Charts":
    st.title("🎯 Shot Analysis")

    selected_season = SEASON

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
            st.plotly_chart(fig_court, width="stretch")

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
        st.plotly_chart(fig, width="stretch")
    with col2:
        fig2 = px.bar(zone_data, x="shot_distance_zone", y="fg_pct", color="zone_group",
                      title="FG% by Shot Zone")
        st.plotly_chart(fig2, width="stretch")

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
    st.plotly_chart(fig3, width="stretch")

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
    st.plotly_chart(fig4, width="stretch")



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
            st.plotly_chart(fig, width="stretch")

            # Rating comparison
            st.subheader("Average Ratings in Matchup")
            avg_stats = h2h[["offensive_rating", "defensive_rating", "net_rating", "pace"]].mean()
            st.dataframe(avg_stats.to_frame("Average").T, width="stretch")
            st.dataframe(h2h, width="stretch")
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
    st.plotly_chart(fig, width="stretch")

    # Efficiency trend
    fig_eff = px.area(pace, x="season", y="avg_efg_pct",
                      title="League-Wide Effective FG% Trend")
    st.plotly_chart(fig_eff, width="stretch")

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
    st.plotly_chart(fig2, width="stretch")

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
    st.plotly_chart(fig3, width="stretch")

    # Points distribution
    st.subheader("Scoring Distribution")
    pts_dist = query("""
        select total_points from main_marts.fct_game_results
    """)
    fig4 = px.histogram(pts_dist, x="total_points", nbins=50,
                        title="Distribution of Total Points Scored per Game",
                        color_discrete_sequence=["#3b82f6"])
    fig4.update_layout(xaxis_title="Total Points", yaxis_title="Games")
    st.plotly_chart(fig4, width="stretch")



# ============================================================
# PAGE: Quarter Analysis
# ============================================================
elif page == "Quarter Analysis":
    st.title("⏱️ Quarter-by-Quarter Analysis")

    selected_season = SEASON

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
        st.plotly_chart(fig, width="stretch")
    with col2:
        fig2 = px.bar(quarter_avg, x="period", y="avg_diff",
                      title="Avg Point Differential by Quarter",
                      color="avg_diff", color_continuous_scale="RdYlGn",
                      labels={"period": "Quarter", "avg_diff": "Avg Differential"})
        st.plotly_chart(fig2, width="stretch")

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
    st.plotly_chart(fig3, width="stretch")

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
        st.plotly_chart(fig4, width="stretch")
        st.dataframe(comebacks, width="stretch")
    else:
        st.info("No comeback data available for this season.")
