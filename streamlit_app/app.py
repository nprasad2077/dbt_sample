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
# PAGE: League Pulse (Overview)
# ============================================================
if page == "Overview":
    st.title(f"📊 League Pulse — {SEASON_LABEL}")

    # --- KPIs with delta vs prior season ---
    summary = query("""
        SELECT count(*) AS total_games,
               sum(CASE WHEN is_overtime THEN 1 ELSE 0 END) AS ot_games,
               round(avg(total_points), 1) AS avg_pts,
               round(avg(point_differential), 1) AS avg_margin,
               round(100.0 * sum(CASE WHEN is_home_team_winner THEN 1 ELSE 0 END) / count(*), 1) AS home_win_pct,
               min(game_date) AS first_game,
               max(game_date) AS last_game
        FROM main_marts.fct_game_results
        WHERE season_key IN (SELECT season_key FROM main_marts.dim_seasons WHERE season_start_year = ?)
    """, [SEASON])

    prior = query("""
        SELECT round(avg(total_points), 1) AS avg_pts,
               round(avg(point_differential), 1) AS avg_margin,
               round(100.0 * sum(CASE WHEN is_home_team_winner THEN 1 ELSE 0 END) / count(*), 1) AS home_win_pct
        FROM main_marts.fct_game_results
        WHERE season_key IN (SELECT season_key FROM main_marts.dim_seasons WHERE season_start_year = ?)
    """, [SEASON - 1])

    has_prior = not prior.empty and prior["avg_pts"][0] is not None
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Games", f"{summary['total_games'][0]:,}")
    c2.metric("Avg Points/Game", summary["avg_pts"][0],
              delta=f"{summary['avg_pts'][0] - prior['avg_pts'][0]:+.1f}" if has_prior else None)
    c3.metric("Avg Margin", summary["avg_margin"][0],
              delta=f"{summary['avg_margin'][0] - prior['avg_margin'][0]:+.1f}" if has_prior else None)
    c4.metric("Home Win %", f"{summary['home_win_pct'][0]}%",
              delta=f"{summary['home_win_pct'][0] - prior['home_win_pct'][0]:+.1f}%" if has_prior else None)
    c5.metric("OT Games", f"{summary['ot_games'][0]:,}")

    st.caption(f"Season: {summary['first_game'][0]} → {summary['last_game'][0]} | Deltas vs prior season")

    # --- Row 2: Competitiveness donut + Top 5 standings ---
    col1, col2 = st.columns(2)

    with col1:
        comp = query("""
            SELECT game_competitiveness_tier AS tier, count(*) AS games
            FROM main_marts.fct_game_results
            WHERE season_key IN (SELECT season_key FROM main_marts.dim_seasons WHERE season_start_year = ?)
            GROUP BY tier ORDER BY games DESC
        """, [SEASON])
        fig = px.pie(comp, names="tier", values="games", title="Game Competitiveness",
                     hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_traces(textinfo="percent+label")
        st.plotly_chart(fig, width="stretch")

    with col2:
        standings = query("""
            SELECT team, count(*) AS games,
                   sum(CASE WHEN game_result = 'W' THEN 1 ELSE 0 END) AS wins,
                   sum(CASE WHEN game_result = 'L' THEN 1 ELSE 0 END) AS losses,
                   round(100.0 * sum(CASE WHEN game_result = 'W' THEN 1 ELSE 0 END) / count(*), 1) AS win_pct,
                   round(avg(net_rating), 1) AS net_rtg
            FROM main_intermediate.int_team_performance
            WHERE season_start_year = ?
            GROUP BY team ORDER BY win_pct DESC LIMIT 8
        """, [SEASON])
        st.subheader("🏆 Top Teams")
        st.dataframe(
            standings,
            column_config={
                "win_pct": st.column_config.ProgressColumn("Win%", min_value=0, max_value=100, format="%.1f%%"),
            },
            hide_index=True, width="stretch",
        )

    # --- Row 3: Weekly scoring trend ---
    weekly = query("""
        SELECT date_trunc('week', game_date)::date::varchar AS week,
               count(*) AS games,
               round(avg(total_points), 1) AS avg_pts,
               round(avg(point_differential), 1) AS avg_margin
        FROM main_marts.fct_game_results
        WHERE season_key IN (SELECT season_key FROM main_marts.dim_seasons WHERE season_start_year = ?)
        GROUP BY week ORDER BY week
    """, [SEASON])
    fig_weekly = px.area(weekly, x="week", y="avg_pts",
                         title="Weekly Scoring Trend", color_discrete_sequence=["#3b82f6"])
    fig_weekly.update_layout(xaxis_title="Week", yaxis_title="Avg Total Points", height=350)
    st.plotly_chart(fig_weekly, width="stretch")

    # --- Row 4: Calendar heatmap + Season highlights ---
    col1, col2 = st.columns([2, 1])

    with col1:
        cal_data = query("""
            SELECT game_date::varchar AS day, count(*) AS games
            FROM main_marts.fct_game_results
            WHERE season_key IN (SELECT season_key FROM main_marts.dim_seasons WHERE season_start_year = ?)
            GROUP BY game_date ORDER BY game_date
        """, [SEASON])
        if not cal_data.empty:
            cal_list = cal_data.values.tolist()
            cal_option = {
                "tooltip": {"position": "top", "formatter": "{c0} games on {b0}"},
                "visualMap": {
                    "min": 0, "max": int(cal_data["games"].max()),
                    "calculable": True, "orient": "horizontal", "left": "center", "top": "top",
                    "inRange": {"color": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]},
                },
                "calendar": {"range": [cal_list[0][0][:7], cal_list[-1][0][:7]],
                             "cellSize": ["auto", 15]},
                "series": [{"type": "heatmap", "coordinateSystem": "calendar", "data": cal_list}],
            }
            st_echarts(options=cal_option, height="200px")

    with col2:
        st.subheader("🔥 Top Performances")
        highlights = query("""
            SELECT player_name AS player, team,
                   game_date::date::varchar AS date, points AS pts,
                   assists AS ast, total_rebounds AS reb
            FROM main_intermediate.int_player_performance
            WHERE season_start_year = ?
            ORDER BY points DESC LIMIT 5
        """, [SEASON])
        st.dataframe(highlights, hide_index=True, width="stretch")

    # --- Row 5: Recent games ---
    st.subheader("Recent Games")
    games = query("""
        SELECT g.game_date, ht.team_abbr AS home, vt.team_abbr AS away,
               g.home_points, g.visitor_points, wt.team_abbr AS winner,
               g.point_differential AS margin, g.game_competitiveness_tier AS type
        FROM main_marts.fct_game_results g
        LEFT JOIN main_marts.dim_teams ht ON g.home_team_key = ht.team_key
        LEFT JOIN main_marts.dim_teams vt ON g.visitor_team_key = vt.team_key
        LEFT JOIN main_marts.dim_teams wt ON g.winning_team_key = wt.team_key
        WHERE g.season_key IN (SELECT season_key FROM main_marts.dim_seasons WHERE season_start_year = ?)
        ORDER BY g.game_date DESC LIMIT 25
    """, [SEASON])
    st.dataframe(games, hide_index=True, width="stretch")



# ============================================================
# PAGE: Teams
# ============================================================
# PAGE: Teams
# ============================================================
elif page == "Teams":
    st.title(f"🏆 Team Intelligence — {SEASON_LABEL}")

    # --- Core ratings data (parameterized, all four factors) ---
    ratings = query("""
        SELECT team, count(*) AS games,
               sum(CASE WHEN game_result = 'W' THEN 1 ELSE 0 END) AS wins,
               sum(CASE WHEN game_result = 'L' THEN 1 ELSE 0 END) AS losses,
               round(100.0 * sum(CASE WHEN game_result = 'W' THEN 1 ELSE 0 END) / count(*), 1) AS win_pct,
               round(avg(offensive_rating), 1) AS off_rtg,
               round(avg(defensive_rating), 1) AS def_rtg,
               round(avg(net_rating), 1) AS net_rtg,
               round(avg(pace), 1) AS pace,
               round(avg(effective_fg_pct) * 100, 1) AS efg_pct,
               round(avg(turnover_rate) * 100, 1) AS tov_rate,
               round(avg(offensive_rebound_rate) * 100, 1) AS orb_rate,
               round(avg(free_throw_rate) * 100, 1) AS ft_rate
        FROM main_intermediate.int_team_performance
        WHERE season_start_year = ?
        GROUP BY team ORDER BY net_rtg DESC
    """, [SEASON])

    tab_ratings, tab_factors, tab_drilldown = st.tabs(
        ["📊 Ratings & Standings", "📐 Four Factors & Styles", "🔍 Team Drill-Down"]
    )

    # --- TAB: Ratings & Standings ---
    with tab_ratings:
        # Offense vs Defense quadrant scatter — the key chart
        fig = px.scatter(
            ratings, x="off_rtg", y="def_rtg", text="team",
            size="win_pct", color="net_rtg", color_continuous_scale="RdYlGn",
            title="Offensive vs Defensive Rating (size = Win%)",
        )
        fig.update_traces(textposition="top center", marker=dict(sizemin=8))
        avg_off = ratings["off_rtg"].mean()
        avg_def = ratings["def_rtg"].mean()
        fig.add_hline(y=avg_def, line_dash="dash", line_color="gray", opacity=0.4)
        fig.add_vline(x=avg_off, line_dash="dash", line_color="gray", opacity=0.4)
        fig.update_layout(
            xaxis_title="Offensive Rating → (higher = better)",
            yaxis_title="← Defensive Rating (lower = better)",
            yaxis=dict(autorange="reversed"), height=550,
        )
        st.plotly_chart(fig, width="stretch")

        # Win% bar for all teams
        win_sorted = ratings.sort_values("win_pct", ascending=True)
        fig_win = px.bar(win_sorted, x="win_pct", y="team", orientation="h",
                         color="net_rtg", color_continuous_scale="RdYlGn",
                         title="Win % (color = Net Rating)")
        fig_win.update_layout(height=600, yaxis_title="", xaxis_title="Win %")
        fig_win.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
        st.plotly_chart(fig_win, width="stretch")

        # Standings table with progress columns
        st.dataframe(
            ratings,
            column_config={
                "win_pct": st.column_config.ProgressColumn("Win%", min_value=0, max_value=100, format="%.1f%%"),
                "efg_pct": st.column_config.ProgressColumn("eFG%", min_value=45, max_value=60, format="%.1f%%"),
            },
            hide_index=True, width="stretch",
        )

    # --- TAB: Four Factors & Styles ---
    with tab_factors:
        st.subheader("Four Factors")
        st.caption("The four key drivers of team success: eFG%, Turnover Rate, Offensive Rebound Rate, Free Throw Rate")

        # 2x2 grid for all four factors
        col1, col2 = st.columns(2)
        with col1:
            top10 = ratings.nlargest(10, "efg_pct")
            fig = px.bar(top10, x="efg_pct", y="team", orientation="h",
                         color="efg_pct", color_continuous_scale="Greens",
                         title="eFG% (Top 10)")
            fig.update_layout(yaxis=dict(autorange="reversed"), height=350, showlegend=False)
            st.plotly_chart(fig, width="stretch")
        with col2:
            top10 = ratings.nsmallest(10, "tov_rate")
            fig = px.bar(top10, x="tov_rate", y="team", orientation="h",
                         color="tov_rate", color_continuous_scale="Reds_r",
                         title="Turnover Rate (Top 10 — lowest)")
            fig.update_layout(yaxis=dict(autorange="reversed"), height=350, showlegend=False)
            st.plotly_chart(fig, width="stretch")

        col3, col4 = st.columns(2)
        with col3:
            top10 = ratings.nlargest(10, "orb_rate")
            fig = px.bar(top10, x="orb_rate", y="team", orientation="h",
                         color="orb_rate", color_continuous_scale="Purples",
                         title="Offensive Rebound Rate (Top 10)")
            fig.update_layout(yaxis=dict(autorange="reversed"), height=350, showlegend=False)
            st.plotly_chart(fig, width="stretch")
        with col4:
            top10 = ratings.nlargest(10, "ft_rate")
            fig = px.bar(top10, x="ft_rate", y="team", orientation="h",
                         color="ft_rate", color_continuous_scale="Oranges",
                         title="Free Throw Rate (Top 10)")
            fig.update_layout(yaxis=dict(autorange="reversed"), height=350, showlegend=False)
            st.plotly_chart(fig, width="stretch")

        # Play style sunbursts
        st.subheader("Team Styles")
        col1, col2 = st.columns(2)
        with col1:
            styles = query("""
                SELECT shot_selection_style, ball_movement_style, count(*) AS games,
                       round(avg(CASE WHEN game_result = 'W' THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_pct
                FROM main_intermediate.int_team_performance
                WHERE season_start_year = ?
                GROUP BY shot_selection_style, ball_movement_style
                ORDER BY win_pct DESC
            """, [SEASON])
            fig = px.sunburst(styles, path=["shot_selection_style", "ball_movement_style"],
                              values="games", color="win_pct", color_continuous_scale="RdYlGn",
                              title="Offense: Shot Selection × Ball Movement")
            st.plotly_chart(fig, width="stretch")

        with col2:
            defense = query("""
                SELECT defensive_activity, ball_movement_style, count(*) AS games,
                       round(avg(CASE WHEN game_result = 'W' THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_pct
                FROM main_intermediate.int_team_performance
                WHERE season_start_year = ?
                GROUP BY defensive_activity, ball_movement_style
                ORDER BY win_pct DESC
            """, [SEASON])
            fig = px.sunburst(defense, path=["defensive_activity", "ball_movement_style"],
                              values="games", color="win_pct", color_continuous_scale="RdYlGn",
                              title="Defense: Activity × Ball Movement")
            st.plotly_chart(fig, width="stretch")

    # --- TAB: Team Drill-Down ---
    with tab_drilldown:
        team_list = ratings["team"].tolist()
        selected_team = st.selectbox("Select Team", team_list)

        # Rolling 10-game trajectory
        trajectory = query("""
            SELECT game_date::date::varchar AS game_date,
                   round(net_rating, 1) AS net_rtg,
                   round(avg(net_rating) OVER (
                       ORDER BY game_date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                   ), 1) AS rolling_net_rtg,
                   round(avg(offensive_rating) OVER (
                       ORDER BY game_date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                   ), 1) AS rolling_off,
                   round(avg(defensive_rating) OVER (
                       ORDER BY game_date ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
                   ), 1) AS rolling_def
            FROM main_intermediate.int_team_performance
            WHERE season_start_year = ? AND team = ?
            ORDER BY game_date
        """, [SEASON, selected_team])

        if not trajectory.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trajectory["game_date"], y=trajectory["rolling_net_rtg"],
                name="Net Rating", mode="lines", line=dict(color="#3b82f6", width=3),
            ))
            fig.add_trace(go.Scatter(
                x=trajectory["game_date"], y=trajectory["rolling_off"],
                name="Offense", mode="lines", line=dict(color="#22c55e", width=1.5, dash="dot"),
            ))
            fig.add_trace(go.Scatter(
                x=trajectory["game_date"], y=trajectory["rolling_def"],
                name="Defense", mode="lines", line=dict(color="#ef4444", width=1.5, dash="dot"),
            ))
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.4)
            fig.update_layout(
                title=f"{selected_team} — 10-Game Rolling Ratings",
                xaxis_title="Date", yaxis_title="Rating", height=400,
            )
            st.plotly_chart(fig, width="stretch")

        # Game log
        st.subheader(f"{selected_team} Game Log")
        game_log = query("""
            SELECT game_date::date::varchar AS date, opponent_team AS opp, game_result AS result,
                   points AS pts, round(offensive_rating, 1) AS off_rtg,
                   round(defensive_rating, 1) AS def_rtg, round(net_rating, 1) AS net_rtg,
                   round(pace, 1) AS pace
            FROM main_intermediate.int_team_performance
            WHERE season_start_year = ? AND team = ?
            ORDER BY game_date DESC
        """, [SEASON, selected_team])
        st.dataframe(game_log, hide_index=True, width="stretch")



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
# PAGE: Shot Studio
# ============================================================
elif page == "Shot Charts":
    st.title(f"🎯 Shot Studio — {SEASON_LABEL}")

    tab_chart, tab_zones, tab_clutch = st.tabs(
        ["🏀 Shot Chart", "📊 Zone & Profile Analysis", "⏱️ Clutch Shooting"]
    )

    # --- TAB: Shot Chart ---
    with tab_chart:
        top_shooters = query("""
            SELECT p.player_name, count(*) AS shots
            FROM main_marts.fct_player_shots s
            JOIN main_marts.dim_players p ON s.player_key = p.player_key
            JOIN main_marts.dim_seasons sea ON s.season_key = sea.season_key
            WHERE sea.season_start_year = ? AND s.shot_source = 'shot_chart'
            GROUP BY p.player_name HAVING count(*) >= 50
            ORDER BY shots DESC
        """, [SEASON])

        if not top_shooters.empty:
            selected_player = st.selectbox("Player", top_shooters["player_name"].tolist())

            shot_data = query("""
                SELECT s.shot_x_coordinate AS x, s.shot_y_coordinate AS y,
                       s.is_made, s.shot_distance_zone, s.distance_ft, s.quarter_number
                FROM main_marts.fct_player_shots s
                JOIN main_marts.dim_players p ON s.player_key = p.player_key
                JOIN main_marts.dim_seasons sea ON s.season_key = sea.season_key
                WHERE sea.season_start_year = ? AND s.shot_source = 'shot_chart'
                      AND p.player_name = ?
            """, [SEASON, selected_player])

            if not shot_data.empty:
                shot_data["result"] = shot_data["is_made"].map({True: "Made", False: "Missed"})

                col1, col2 = st.columns([2, 1])
                with col1:
                    fig = px.scatter(
                        shot_data, x="x", y="y", color="result",
                        color_discrete_map={"Made": "#22c55e", "Missed": "#ef4444"},
                        opacity=0.7, title=f"{selected_player} — Shot Chart ({len(shot_data)} shots)",
                        hover_data=["shot_distance_zone", "distance_ft", "quarter_number"],
                    )
                    fig.update_traces(marker=dict(size=6, line=dict(width=0.5, color="rgba(0,0,0,0.3)")))

                    # --- Draw NBA half-court lines ---
                    # Coordinate system: basket at (240, 55), court width ~480, baseline at y~0
                    import numpy as np
                    court_color = "rgba(255,255,255,0.45)"
                    paint_color = "rgba(255,200,100,0.12)"

                    # Paint / key (16ft wide = ~160 data units, 19ft deep = ~190 units)
                    fig.add_shape(type="rect", x0=160, x1=320, y0=0, y1=190,
                                  line=dict(color=court_color, width=1.5),
                                  fillcolor=paint_color)

                    # Backboard
                    fig.add_shape(type="line", x0=210, x1=270, y0=40, y1=40,
                                  line=dict(color=court_color, width=2))

                    # Basket (rim)
                    fig.add_shape(type="circle", x0=232, x1=248, y0=47, y1=63,
                                  line=dict(color="rgba(255,120,0,0.7)", width=2))

                    # Free throw circle (radius ~60 data units at y=190)
                    theta_ft = np.linspace(0, np.pi, 50)
                    ft_x = 240 + 60 * np.cos(theta_ft)
                    ft_y = 190 + 60 * np.sin(theta_ft)
                    fig.add_trace(go.Scatter(x=ft_x, y=ft_y, mode="lines",
                        line=dict(color=court_color, width=1.5), showlegend=False, hoverinfo="skip"))
                    # Dashed bottom half of FT circle
                    ft_x_b = 240 + 60 * np.cos(-theta_ft)
                    ft_y_b = 190 + 60 * np.sin(-theta_ft)
                    fig.add_trace(go.Scatter(x=ft_x_b, y=ft_y_b, mode="lines",
                        line=dict(color=court_color, width=1, dash="dash"), showlegend=False, hoverinfo="skip"))

                    # Restricted area arc (4ft radius = ~40 data units)
                    theta_ra = np.linspace(0, np.pi, 30)
                    ra_x = 240 + 40 * np.cos(theta_ra)
                    ra_y = 55 + 40 * np.sin(theta_ra)
                    fig.add_trace(go.Scatter(x=ra_x, y=ra_y, mode="lines",
                        line=dict(color=court_color, width=1.5), showlegend=False, hoverinfo="skip"))

                    # Three-point arc (23.75ft = ~238 data units radius from basket)
                    # Corner threes are straight lines from baseline to where the arc begins
                    theta_3_start = np.arcsin(35/238)
                    corner_x_left = 240 - 238 * np.cos(theta_3_start)
                    corner_x_right = 240 + 238 * np.cos(theta_3_start)
                    corner_y = 55 + 35  # y where arc begins
                    fig.add_shape(type="line", x0=corner_x_left, x1=corner_x_left, y0=0, y1=corner_y,
                                  line=dict(color=court_color, width=1.5))
                    fig.add_shape(type="line", x0=corner_x_right, x1=corner_x_right, y0=0, y1=corner_y,
                                  line=dict(color=court_color, width=1.5))
                    # Arc portion
                    theta_3 = np.linspace(theta_3_start, np.pi - theta_3_start, 80)
                    arc_x = 240 + 238 * np.cos(theta_3)
                    arc_y = 55 + 238 * np.sin(theta_3)
                    fig.add_trace(go.Scatter(x=arc_x, y=arc_y, mode="lines",
                        line=dict(color=court_color, width=2), showlegend=False, hoverinfo="skip"))

                    # Half-court line
                    fig.add_shape(type="line", x0=-10, x1=490, y0=470, y1=470,
                                  line=dict(color=court_color, width=1.5))
                    # Center circle (top arc only)
                    theta_cc = np.linspace(np.pi, 2*np.pi, 40)
                    cc_x = 240 + 60 * np.cos(theta_cc)
                    cc_y = 470 + 60 * np.sin(theta_cc)
                    fig.add_trace(go.Scatter(x=cc_x, y=cc_y, mode="lines",
                        line=dict(color=court_color, width=1.5), showlegend=False, hoverinfo="skip"))

                    fig.update_layout(
                        height=600,
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-20, 500]),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False,
                                   range=[-20, 480], scaleanchor="x"),
                        plot_bgcolor="#1a1a2e",
                    )
                    st.plotly_chart(fig, width="stretch")

                with col2:
                    # Per-player zone efficiency vs league
                    st.subheader("Zone Efficiency vs League")
                    zone_comparison = query("""
                        WITH league AS (
                            SELECT s.shot_distance_zone,
                                   round(100.0 * sum(s.is_made::int) / count(*), 1) AS league_fg_pct
                            FROM main_marts.fct_player_shots s
                            JOIN main_marts.dim_seasons sea ON s.season_key = sea.season_key
                            WHERE sea.season_start_year = ? AND s.shot_source = 'shot_chart'
                            GROUP BY s.shot_distance_zone
                        ),
                        player AS (
                            SELECT s.shot_distance_zone, count(*) AS attempts,
                                   round(100.0 * sum(s.is_made::int) / count(*), 1) AS player_fg_pct
                            FROM main_marts.fct_player_shots s
                            JOIN main_marts.dim_players p ON s.player_key = p.player_key
                            JOIN main_marts.dim_seasons sea ON s.season_key = sea.season_key
                            WHERE sea.season_start_year = ? AND s.shot_source = 'shot_chart'
                                  AND p.player_name = ?
                            GROUP BY s.shot_distance_zone
                        )
                        SELECT p.shot_distance_zone AS zone, p.attempts, p.player_fg_pct,
                               l.league_fg_pct, round(p.player_fg_pct - l.league_fg_pct, 1) AS vs_league
                        FROM player p JOIN league l ON p.shot_distance_zone = l.shot_distance_zone
                        ORDER BY p.attempts DESC
                    """, [SEASON, SEASON, selected_player])

                    if not zone_comparison.empty:
                        for _, z in zone_comparison.iterrows():
                            delta_color = "normal" if z["vs_league"] >= 0 else "inverse"
                            st.metric(
                                z["zone"],
                                f"{z['player_fg_pct']}%",
                                delta=f"{z['vs_league']:+.1f}% vs league",
                                delta_color=delta_color,
                            )
        else:
            st.info("No spatial shot chart data available for this season.")

    # --- TAB: Zone & Profile Analysis ---
    with tab_zones:
        # League zone breakdown
        st.subheader("League Zone Efficiency")
        zone_data = query("""
            SELECT sz.shot_distance_zone, sz.zone_group, sz.zone_order,
                   count(*) AS attempts, sum(s.is_made::int) AS makes,
                   round(100.0 * sum(s.is_made::int) / count(*), 1) AS fg_pct,
                   round(avg(s.shot_point_value * s.is_made::int), 3) AS pts_per_shot
            FROM main_marts.fct_player_shots s
            JOIN main_marts.dim_shot_zones sz ON s.shot_distance_zone = sz.shot_distance_zone
            JOIN main_marts.dim_seasons sea ON s.season_key = sea.season_key
            WHERE sea.season_start_year = ?
            GROUP BY sz.shot_distance_zone, sz.zone_group, sz.zone_order
            ORDER BY sz.zone_order
        """, [SEASON])

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(zone_data, x="shot_distance_zone", y="attempts",
                         color="fg_pct", color_continuous_scale="RdYlGn",
                         title="Volume by Zone (color = FG%)")
            st.plotly_chart(fig, width="stretch")
        with col2:
            fig = px.bar(zone_data, x="shot_distance_zone", y="pts_per_shot",
                         color="zone_group", title="Points per Shot by Zone")
            st.plotly_chart(fig, width="stretch")

        # Shot Profile Scatter — player archetypes by shooting style
        st.subheader("Player Shot Profiles")
        profiles = query("""
            SELECT p.player_name,
                   count(*) AS games,
                   round(avg(s.three_point_rate) * 100, 1) AS three_rate,
                   round(avg(s.at_rim_rate) * 100, 1) AS rim_rate,
                   round(avg(s.mid_range_rate) * 100, 1) AS mid_rate,
                   round(avg(s.avg_fg_distance_ft), 1) AS avg_dist,
                   round(avg(s.true_shooting_pct) * 100, 1) AS ts_pct
            FROM main_marts.fct_player_game_shooting s
            JOIN main_marts.dim_players p ON s.player_key = p.player_key
            JOIN main_marts.dim_seasons sea ON s.season_key = sea.season_key
            WHERE sea.season_start_year = ? AND s.fg_attempts >= 10
            GROUP BY p.player_name HAVING count(*) >= 20
            ORDER BY ts_pct DESC
        """, [SEASON])

        if not profiles.empty:
            fig = px.scatter(
                profiles, x="three_rate", y="rim_rate", size="ts_pct",
                hover_name="player_name", color="ts_pct",
                color_continuous_scale="RdYlGn",
                title="Shot Profile Clustering: Three-Point Rate vs Rim Rate (size/color = TS%)",
            )
            fig.update_layout(
                xaxis_title="Three-Point Rate %", yaxis_title="At-Rim Rate %", height=500,
            )
            st.plotly_chart(fig, width="stretch")

        # Shot profile type breakdown (treemap)
        profile_types = query("""
            SELECT shot_profile_type, count(*) AS player_games,
                   round(avg(true_shooting_pct) * 100, 1) AS avg_ts,
                   round(avg(total_points), 1) AS avg_pts
            FROM main_marts.fct_player_game_shooting s
            JOIN main_marts.dim_seasons sea ON s.season_key = sea.season_key
            WHERE sea.season_start_year = ?
            GROUP BY shot_profile_type ORDER BY player_games DESC
        """, [SEASON])
        fig = px.treemap(profile_types, path=["shot_profile_type"], values="player_games",
                         color="avg_ts", color_continuous_scale="RdYlGn",
                         title="Shot Profile Types (size = frequency, color = TS%)")
        st.plotly_chart(fig, width="stretch")

    # --- TAB: Clutch Shooting ---
    with tab_clutch:
        clutch = query("""
            SELECT p.player_name,
                   count(*) AS clutch_attempts,
                   sum(s.is_made::int) AS clutch_makes,
                   round(100.0 * sum(s.is_made::int) / count(*), 1) AS clutch_pct,
                   round(avg(s.score_margin_at_shot), 1) AS avg_margin
            FROM main_marts.fct_player_shots s
            JOIN main_marts.dim_players p ON s.player_key = p.player_key
            JOIN main_marts.dim_seasons sea ON s.season_key = sea.season_key
            WHERE s.is_clutch_shot AND sea.season_start_year = ?
            GROUP BY p.player_name HAVING count(*) >= 15
            ORDER BY clutch_makes DESC LIMIT 30
        """, [SEASON])

        if not clutch.empty:
            fig = px.scatter(
                clutch, x="clutch_attempts", y="clutch_pct",
                size="clutch_makes", hover_name="player_name",
                color="clutch_pct", color_continuous_scale="RdYlGn",
                title="Clutch Shooting: Volume vs Accuracy",
            )
            fig.add_hline(y=clutch["clutch_pct"].median(), line_dash="dash",
                          line_color="gray", annotation_text="Median")
            fig.update_layout(
                xaxis_title="Clutch Attempts", yaxis_title="Clutch FG%", height=500,
            )
            st.plotly_chart(fig, width="stretch")

            # Clutch leaderboard table
            st.subheader("Clutch Leaders")
            st.dataframe(
                clutch[["player_name", "clutch_attempts", "clutch_makes", "clutch_pct", "avg_margin"]],
                hide_index=True, width="stretch",
                column_config={
                    "clutch_pct": st.column_config.ProgressColumn(
                        "FG%", min_value=25, max_value=65, format="%.1f%%"
                    ),
                },
            )
        else:
            st.info("No clutch shooting data available for this season.")



# ============================================================
# PAGE: Head to Head
# ============================================================
# PAGE: Matchups
# ============================================================
elif page == "Head to Head":
    st.title(f"⚔️ Matchup Center — {SEASON_LABEL}")

    teams = query("SELECT DISTINCT team FROM main_intermediate.int_team_performance ORDER BY team")
    team_list = teams["team"].tolist()

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        team_a = st.selectbox("Team A", team_list, index=0)
    with col2:
        team_b = st.selectbox("Team B", team_list, index=min(1, len(team_list) - 1))
    with col3:
        scope = st.radio("Scope", ["This Season", "All-Time"], horizontal=False)

    if team_a == team_b:
        st.warning("Select two different teams.")
    else:
        season_filter = "AND season_start_year = ?" if scope == "This Season" else ""
        season_filter_tp = "AND tp.season_start_year = ?" if scope == "This Season" else ""
        season_params = [SEASON] if scope == "This Season" else []

        # --- Aggregate stats for both teams ---
        h2h_agg = query(f"""
            SELECT team, count(*) AS games,
                   sum(CASE WHEN game_result = 'W' THEN 1 ELSE 0 END) AS wins,
                   round(avg(points), 1) AS avg_pts,
                   round(avg(offensive_rating), 1) AS off_rtg,
                   round(avg(defensive_rating), 1) AS def_rtg,
                   round(avg(net_rating), 1) AS net_rtg,
                   round(avg(pace), 1) AS pace,
                   round(avg(effective_fg_pct) * 100, 1) AS efg_pct,
                   round(avg(turnover_rate) * 100, 1) AS tov_rate
            FROM main_intermediate.int_team_performance
            WHERE ((team = ? AND opponent_team = ?) OR (team = ? AND opponent_team = ?))
                  {season_filter}
            GROUP BY team
        """, [team_a, team_b, team_b, team_a] + season_params)

        if h2h_agg.empty or len(h2h_agg) < 2:
            st.info("No matchup history found between these teams for this scope.")
        else:
            row_a = h2h_agg[h2h_agg["team"] == team_a].iloc[0]
            row_b = h2h_agg[h2h_agg["team"] == team_b].iloc[0]

            # KPIs
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(f"{team_a} Wins", int(row_a["wins"]))
            c2.metric(f"{team_a} PPG", row_a["avg_pts"])
            c3.metric("Games", int(row_a["games"]))
            c4.metric(f"{team_b} PPG", row_b["avg_pts"])
            c5.metric(f"{team_b} Wins", int(row_b["wins"]))

            tab_compare, tab_games, tab_players = st.tabs(
                ["📊 Comparison", "📋 Game Log", "👤 Key Players"]
            )

            # --- TAB: Comparison radar ---
            with tab_compare:
                categories = ["avg_pts", "off_rtg", "pace", "efg_pct"]
                # For def_rtg and tov_rate, lower is better — invert for radar
                cat_labels = ["Points", "Off Rating", "Pace", "eFG%", "Def Rating (inv)", "Low TOV (inv)"]
                vals_a = [float(row_a["avg_pts"]), float(row_a["off_rtg"]), float(row_a["pace"]),
                          float(row_a["efg_pct"]), 130 - float(row_a["def_rtg"]), 20 - float(row_a["tov_rate"])]
                vals_b = [float(row_b["avg_pts"]), float(row_b["off_rtg"]), float(row_b["pace"]),
                          float(row_b["efg_pct"]), 130 - float(row_b["def_rtg"]), 20 - float(row_b["tov_rate"])]

                radar_option = {
                    "legend": {"data": [team_a, team_b], "top": "bottom"},
                    "color": ["#3b82f6", "#ef4444"],
                    "radar": {
                        "indicator": [
                            {"name": "Points", "max": max(vals_a[0], vals_b[0]) * 1.15},
                            {"name": "Off Rating", "max": max(vals_a[1], vals_b[1]) * 1.1},
                            {"name": "Pace", "max": max(vals_a[2], vals_b[2]) * 1.1},
                            {"name": "eFG%", "max": max(vals_a[3], vals_b[3]) * 1.15},
                            {"name": "Defense (inv)", "max": max(vals_a[4], vals_b[4]) * 1.15},
                            {"name": "Ball Security (inv)", "max": max(vals_a[5], vals_b[5]) * 1.15},
                        ],
                        "shape": "polygon",
                        "splitArea": {"areaStyle": {"color": ["#1a1a2e", "#16213e", "#0f3460", "#1a1a2e"]}},
                        "axisLine": {"lineStyle": {"color": "rgba(200,200,200,0.3)"}},
                        "splitLine": {"lineStyle": {"color": "rgba(200,200,200,0.2)"}},
                    },
                    "series": [{"type": "radar", "data": [
                        {"value": vals_a, "name": team_a,
                         "lineStyle": {"color": "#3b82f6", "width": 2.5},
                         "areaStyle": {"color": "#3b82f6", "opacity": 0.25},
                         "itemStyle": {"color": "#3b82f6"}},
                        {"value": vals_b, "name": team_b,
                         "lineStyle": {"color": "#ef4444", "width": 2.5},
                         "areaStyle": {"color": "#ef4444", "opacity": 0.25},
                         "itemStyle": {"color": "#ef4444"}},
                    ]}],
                }
                st_echarts(options=radar_option, height="450px")

                # Side-by-side stat comparison
                st.dataframe(
                    h2h_agg.set_index("team")[["games", "wins", "avg_pts", "off_rtg", "def_rtg", "net_rtg", "pace", "efg_pct", "tov_rate"]],
                    width="stretch",
                )

            # --- TAB: Game Log ---
            with tab_games:
                game_log = query(f"""
                    SELECT g.game_date::date::varchar AS date,
                           ht.team_abbr AS home, vt.team_abbr AS away,
                           g.home_points, g.visitor_points, wt.team_abbr AS winner,
                           g.point_differential AS margin,
                           g.game_competitiveness_tier AS type
                    FROM main_marts.fct_game_results g
                    JOIN main_marts.dim_teams ht ON g.home_team_key = ht.team_key
                    JOIN main_marts.dim_teams vt ON g.visitor_team_key = vt.team_key
                    JOIN main_marts.dim_teams wt ON g.winning_team_key = wt.team_key
                    {"JOIN main_marts.dim_seasons s ON g.season_key = s.season_key" if scope == "This Season" else ""}
                    WHERE ((ht.team_abbr = ? AND vt.team_abbr = ?) OR (ht.team_abbr = ? AND vt.team_abbr = ?))
                          {"AND s.season_start_year = ?" if scope == "This Season" else ""}
                    ORDER BY g.game_date DESC
                """, [team_a, team_b, team_b, team_a] + season_params)

                if not game_log.empty:
                    # Margin chart
                    game_log["winner_color"] = game_log["winner"].apply(
                        lambda w: team_a if w == team_a else team_b
                    )
                    fig = px.bar(game_log, x="date", y="margin", color="winner_color",
                                 color_discrete_map={team_a: "#3b82f6", team_b: "#ef4444"},
                                 title="Game Margins (color = winner)")
                    fig.update_layout(xaxis_title="", yaxis_title="Point Margin", height=350)
                    st.plotly_chart(fig, width="stretch")

                    st.dataframe(game_log.drop(columns=["winner_color"]), hide_index=True, width="stretch")

            # --- TAB: Key Players ---
            with tab_players:
                players_in_matchup = query(f"""
                    SELECT pp.player_name, pp.team, count(*) AS games,
                           round(avg(pp.points), 1) AS ppg,
                           round(avg(pp.assists), 1) AS apg,
                           round(avg(pp.total_rebounds), 1) AS rpg,
                           round(avg(pp.box_plus_minus), 2) AS bpm
                    FROM main_intermediate.int_player_performance pp
                    JOIN main_intermediate.int_team_performance tp
                        ON pp.game_id = tp.game_id AND pp.team = tp.team
                    WHERE ((tp.team = ? AND tp.opponent_team = ?)
                        OR (tp.team = ? AND tp.opponent_team = ?))
                          {season_filter_tp}
                          AND pp.minutes_played >= 15
                    GROUP BY pp.player_name, pp.team
                    HAVING count(*) >= 2
                    ORDER BY ppg DESC LIMIT 15
                """, [team_a, team_b, team_b, team_a] + season_params)

                if not players_in_matchup.empty:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader(f"{team_a} Performers")
                        team_a_players = players_in_matchup[players_in_matchup["team"] == team_a]
                        st.dataframe(
                            team_a_players[["player_name", "games", "ppg", "apg", "rpg", "bpm"]],
                            hide_index=True, width="stretch",
                        )
                    with col2:
                        st.subheader(f"{team_b} Performers")
                        team_b_players = players_in_matchup[players_in_matchup["team"] == team_b]
                        st.dataframe(
                            team_b_players[["player_name", "games", "ppg", "apg", "rpg", "bpm"]],
                            hide_index=True, width="stretch",
                        )
                else:
                    st.info("No player data available for this matchup scope.")



# ============================================================
# PAGE: Game Trends
# ============================================================
# PAGE: Era Trends
# ============================================================
elif page == "Game Trends":
    st.title("📈 Era Trends")

    tab_scoring, tab_drama, tab_three = st.tabs(
        ["🏀 Scoring & Pace", "🎭 Game Character", "🎯 Three-Point Era"]
    )

    # --- TAB: Scoring & Pace ---
    with tab_scoring:
        pace = query("""
            SELECT s.season_display AS season, s.season_start_year,
                   round(avg(g.matchup_pace), 1) AS avg_pace,
                   round(avg(g.total_points), 1) AS avg_points,
                   round(avg(g.home_effective_fg_pct + g.visitor_effective_fg_pct) / 2 * 100, 1) AS avg_efg_pct
            FROM main_intermediate.int_games_enriched g
            JOIN main_marts.dim_seasons s ON g.season_start_year = s.season_start_year
            GROUP BY s.season_display, s.season_start_year
            ORDER BY s.season_start_year
        """)

        # Dual-axis: points + pace
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pace["season"], y=pace["avg_points"],
            name="Avg Points/Game", mode="lines+markers",
            line=dict(color="#3b82f6", width=3),
        ))
        fig.add_trace(go.Scatter(
            x=pace["season"], y=pace["avg_pace"],
            name="Pace", mode="lines+markers", yaxis="y2",
            line=dict(color="#f59e0b", width=2, dash="dot"),
        ))
        fig.update_layout(
            title="Scoring & Pace Evolution",
            yaxis=dict(title="Avg Points/Game"),
            yaxis2=dict(title="Pace (possessions/48min)", overlaying="y", side="right"),
            height=450,
        )
        st.plotly_chart(fig, width="stretch")

        # eFG% trend
        pace_clean = pace.dropna(subset=["avg_efg_pct"])
        fig_eff = px.area(pace_clean, x="season", y="avg_efg_pct",
                          title="League eFG% Trend", color_discrete_sequence=["#10b981"])
        fig_eff.update_layout(yaxis_title="eFG%", height=350)
        st.plotly_chart(fig_eff, width="stretch")

    # --- TAB: Game Character ---
    with tab_drama:
        drama = query("""
            SELECT s.season_display AS season,
                   round(100.0 * sum(CASE WHEN g.is_overtime THEN 1 ELSE 0 END) / count(*), 1) AS ot_pct,
                   round(100.0 * sum(CASE WHEN g.point_differential <= 5 THEN 1 ELSE 0 END) / count(*), 1) AS clutch_pct,
                   round(100.0 * sum(CASE WHEN g.point_differential >= 20 THEN 1 ELSE 0 END) / count(*), 1) AS blowout_pct
            FROM main_intermediate.int_games_enriched g
            JOIN main_marts.dim_seasons s ON g.season_start_year = s.season_start_year
            GROUP BY s.season_display, s.season_start_year
            ORDER BY s.season_start_year
        """)
        fig = px.area(
            drama, x="season", y=["clutch_pct", "blowout_pct", "ot_pct"],
            title="Game Drama: Clutch (≤5pt margin) vs Blowouts (20+) vs Overtime",
            color_discrete_sequence=["#22c55e", "#ef4444", "#a855f7"],
        )
        fig.update_layout(yaxis_title="% of Games", legend_title="Category", height=450)
        st.plotly_chart(fig, width="stretch")

        # Home court advantage
        home = query("""
            SELECT s.season_display AS season,
                   round(100.0 * sum(CASE WHEN g.is_home_team_winner THEN 1 ELSE 0 END) / count(*), 1) AS home_win_pct
            FROM main_marts.fct_game_results g
            JOIN main_marts.dim_seasons s ON g.season_key = s.season_key
            GROUP BY s.season_display, s.season_start_year
            ORDER BY s.season_start_year
        """)
        fig2 = px.line(home, x="season", y="home_win_pct",
                       title="Home Court Advantage Over Time", markers=True)
        fig2.update_layout(yaxis_range=[40, 70], height=400)
        fig2.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="50%")
        st.plotly_chart(fig2, width="stretch")

    # --- TAB: Three-Point Era ---
    with tab_three:
        three_pt = query("""
            SELECT s.season_display AS season, s.season_start_year,
                   round(avg(three_point_rate) * 100, 1) AS avg_three_rate,
                   round(avg(CASE WHEN three_point_fg_pct > 0 THEN three_point_fg_pct ELSE NULL END) * 100, 1) AS avg_three_pct,
                   round(avg(three_point_attempts), 1) AS avg_3pa
            FROM main_marts.fct_player_game_shooting sh
            JOIN main_marts.dim_seasons s ON sh.season_key = s.season_key
            WHERE sh.fg_attempts >= 5
            GROUP BY s.season_display, s.season_start_year
            ORDER BY s.season_start_year
        """)

        if not three_pt.empty:
            # Dual-axis: three-point rate + accuracy
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=three_pt["season"], y=three_pt["avg_three_rate"],
                name="3PA Rate (%)", marker_color="#3b82f6", opacity=0.7,
            ))
            fig.add_trace(go.Scatter(
                x=three_pt["season"], y=three_pt["avg_three_pct"],
                name="3P Accuracy (%)", mode="lines+markers", yaxis="y2",
                line=dict(color="#22c55e", width=3),
            ))
            fig.update_layout(
                title="The Three-Point Revolution: Volume vs Accuracy",
                yaxis=dict(title="3PA Rate (% of all FGA)"),
                yaxis2=dict(title="3P FG%", overlaying="y", side="right",
                            range=[30, 50]),
                height=450, barmode="overlay",
            )
            st.plotly_chart(fig, width="stretch")

            # Average 3PA per player-game trend
            fig2 = px.area(three_pt, x="season", y="avg_3pa",
                           title="Avg Three-Point Attempts per Player-Game",
                           color_discrete_sequence=["#8b5cf6"])
            fig2.update_layout(yaxis_title="3PA per Game", height=350)
            st.plotly_chart(fig2, width="stretch")
        else:
            st.info("Three-point shooting data not available.")



# ============================================================
# PAGE: Quarter Analysis
# ============================================================
# PAGE: Momentum (Quarter Analysis)
# ============================================================
elif page == "Quarter Analysis":
    st.title(f"⏱️ Momentum — {SEASON_LABEL}")

    tab_overview, tab_teams, tab_comebacks = st.tabs(
        ["📊 Quarter Scoring", "🏆 Team by Quarter", "🔄 Comebacks"]
    )

    # --- TAB: Quarter Scoring ---
    with tab_overview:
        quarter_avg = query("""
            SELECT q.period,
                   round(avg(q.points_scored), 1) AS avg_pts,
                   round(avg(abs(q.period_point_differential)), 1) AS avg_abs_diff,
                   round(stddev(q.points_scored), 1) AS scoring_volatility
            FROM main_marts.fct_quarter_scoring q
            JOIN main_marts.dim_seasons s ON q.season_key = s.season_key
            WHERE s.season_start_year = ? AND q.period IN ('Q1','Q2','Q3','Q4')
            GROUP BY q.period ORDER BY q.period
        """, [SEASON])

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(quarter_avg, x="period", y="avg_pts",
                         title="Avg Points per Quarter",
                         color="period",
                         color_discrete_map={"Q1": "#3b82f6", "Q2": "#8b5cf6", "Q3": "#f59e0b", "Q4": "#ef4444"},
                         labels={"period": "Quarter", "avg_pts": "Avg Points"})
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, width="stretch")
        with col2:
            fig2 = px.bar(quarter_avg, x="period", y="avg_abs_diff",
                          title="Avg Quarter Lopsidedness (|differential|)",
                          color="period",
                          color_discrete_map={"Q1": "#3b82f6", "Q2": "#8b5cf6", "Q3": "#f59e0b", "Q4": "#ef4444"},
                          labels={"period": "Quarter", "avg_abs_diff": "Avg |Differential|"})
            fig2.update_layout(showlegend=False)
            st.plotly_chart(fig2, width="stretch")

        st.caption("Q4 has lower scoring and tighter margins — games tighten up in crunch time.")

    # --- TAB: Team by Quarter ---
    with tab_teams:
        quarter_sel = st.radio("Quarter", ["Q1", "Q2", "Q3", "Q4"], horizontal=True)

        team_quarter = query("""
            SELECT t.team_abbr AS team,
                   round(avg(q.points_scored), 1) AS avg_pts,
                   round(avg(q.period_point_differential), 2) AS avg_diff,
                   count(*) AS games
            FROM main_marts.fct_quarter_scoring q
            JOIN main_marts.dim_teams t ON q.team_key = t.team_key
            JOIN main_marts.dim_seasons s ON q.season_key = s.season_key
            WHERE s.season_start_year = ? AND q.period = ?
            GROUP BY t.team_abbr HAVING count(*) >= 10
            ORDER BY avg_diff DESC
        """, [SEASON, quarter_sel])

        fig = px.bar(team_quarter, x="avg_pts", y="team", orientation="h",
                     color="avg_diff", color_continuous_scale="RdYlGn",
                     title=f"{quarter_sel} Leaders — sorted by differential (color = +/-)")
        fig.update_layout(yaxis=dict(autorange="reversed"), height=600)
        st.plotly_chart(fig, width="stretch")

    # --- TAB: Comebacks ---
    with tab_comebacks:
        comebacks = query("""
            WITH q3_trailing AS (
                SELECT q.game_id, q.team_key,
                       sum(q.period_point_differential) AS through_q3_diff
                FROM main_marts.fct_quarter_scoring q
                JOIN main_marts.dim_seasons s ON q.season_key = s.season_key
                WHERE s.season_start_year = ? AND q.period IN ('Q1','Q2','Q3')
                GROUP BY q.game_id, q.team_key
                HAVING sum(q.period_point_differential) < -10
            ),
            q4_results AS (
                SELECT q.game_id, q.team_key, q.period_point_differential AS q4_diff
                FROM main_marts.fct_quarter_scoring q
                JOIN main_marts.dim_seasons s ON q.season_key = s.season_key
                WHERE s.season_start_year = ? AND q.period = 'Q4'
            )
            SELECT t.team_abbr AS team,
                   count(*) AS trailing_10_after_q3,
                   sum(CASE WHEN c.through_q3_diff + r.q4_diff > 0 THEN 1 ELSE 0 END) AS comebacks,
                   round(100.0 * sum(CASE WHEN c.through_q3_diff + r.q4_diff > 0 THEN 1 ELSE 0 END) / count(*), 1) AS comeback_pct
            FROM q3_trailing c
            JOIN q4_results r ON c.game_id = r.game_id AND c.team_key = r.team_key
            JOIN main_marts.dim_teams t ON c.team_key = t.team_key
            GROUP BY t.team_abbr HAVING count(*) >= 3
            ORDER BY comeback_pct DESC
        """, [SEASON, SEASON])

        if not comebacks.empty:
            fig = px.bar(comebacks, x="team", y="comeback_pct",
                         color="comebacks", color_continuous_scale="Greens",
                         title="Comeback Rate (Down 10+ After Q3)")
            fig.update_layout(xaxis_title="", yaxis_title="Comeback %")
            st.plotly_chart(fig, width="stretch")
            st.dataframe(comebacks, hide_index=True, width="stretch")
        else:
            st.info("No comeback data available for this season.")
