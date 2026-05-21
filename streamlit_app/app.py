import streamlit as st
import duckdb
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="NBA Analytics", page_icon="🏀", layout="wide")

DB_PATH = str(Path(__file__).resolve().parent.parent / "dbt_nba" / "reports" / "sources" / "nba" / "dbt_nba.duckdb")


@st.cache_resource
def get_connection():
    return duckdb.connect(DB_PATH, read_only=True)


conn = get_connection()


@st.cache_data
def query(sql):
    return conn.execute(sql).df()


# --- Sidebar ---
st.sidebar.title("🏀 NBA Analytics")
page = st.sidebar.radio("Navigate", ["Overview", "Teams", "Players", "Game Trends"])

# --- Overview ---
if page == "Overview":
    st.title("🏀 NBA Analytics Dashboard")

    summary = query("""
        select count(*) as total_games,
               sum(case when is_overtime then 1 else 0 end) as overtime_games,
               round(avg(total_points), 1) as avg_total_points,
               round(avg(point_differential), 1) as avg_margin
        from main_marts.fct_game_results
    """)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Games", f"{summary['total_games'][0]:,}")
    c2.metric("Avg Points/Game", summary["avg_total_points"][0])
    c3.metric("OT Games", f"{summary['overtime_games'][0]:,}")
    c4.metric("Avg Margin", summary["avg_margin"][0])

    st.subheader("Recent Games")
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

# --- Teams ---
elif page == "Teams":
    st.title("Team Power Rankings")

    ratings = query("""
        select team, count(*) as games,
               sum(case when game_result = 'W' then 1 else 0 end) as wins,
               round(100.0 * sum(case when game_result = 'W' then 1 else 0 end) / count(*), 1) as win_pct,
               round(avg(offensive_rating), 1) as off_rtg,
               round(avg(defensive_rating), 1) as def_rtg,
               round(avg(net_rating), 1) as net_rtg,
               round(avg(pace), 1) as pace
        from main_intermediate.int_team_performance
        where season_start_year = (select max(season_start_year) from main_intermediate.int_team_performance)
        group by team order by net_rtg desc
    """)

    fig = px.bar(ratings, x="net_rtg", y="team", orientation="h",
                 color="net_rtg", color_continuous_scale="RdYlGn",
                 title="Net Rating by Team (Current Season)")
    fig.update_layout(yaxis=dict(autorange="reversed"), height=700)
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(ratings, use_container_width=True)

# --- Players ---
elif page == "Players":
    st.title("Player Impact")

    players = query("""
        select player_name, team, count(*) as games,
               round(avg(points), 1) as ppg,
               round(avg(assists), 1) as apg,
               round(avg(total_rebounds), 1) as rpg,
               round(avg(box_plus_minus), 2) as bpm,
               round(avg(usage_pct), 1) as usage,
               round(avg(true_shooting_pct) * 100, 1) as ts_pct
        from main_intermediate.int_player_performance
        where season_start_year = (select max(season_start_year) from main_intermediate.int_player_performance)
          and minutes_played >= 20
        group by player_name, team
        having count(*) >= 20
        order by bpm desc limit 50
    """)

    fig = px.scatter(players, x="usage", y="ts_pct", size="ppg",
                     hover_name="player_name", color="bpm",
                     color_continuous_scale="RdYlGn",
                     title="Usage Rate vs True Shooting % (size = PPG)")
    fig.update_layout(xaxis_title="Usage %", yaxis_title="True Shooting %")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(players, use_container_width=True)

# --- Game Trends ---
elif page == "Game Trends":
    st.title("League Trends Over Time")

    pace = query("""
        select season_start_year || '-' || substr(cast(season_start_year + 1 as varchar), 3, 2) as season,
               round(avg(matchup_pace), 1) as avg_pace,
               round(avg(total_points), 1) as avg_points,
               round(avg(home_effective_fg_pct + visitor_effective_fg_pct) / 2 * 100, 1) as avg_efg_pct
        from main_intermediate.int_games_enriched
        group by season_start_year order by season_start_year
    """)

    fig = px.line(pace, x="season", y=["avg_points", "avg_pace"],
                  title="Scoring & Pace Evolution")
    st.plotly_chart(fig, use_container_width=True)

    drama = query("""
        select season_start_year || '-' || substr(cast(season_start_year + 1 as varchar), 3, 2) as season,
               round(100.0 * sum(case when is_overtime then 1 else 0 end) / count(*), 1) as ot_pct,
               round(100.0 * sum(case when point_differential <= 5 then 1 else 0 end) / count(*), 1) as clutch_pct,
               round(100.0 * sum(case when point_differential >= 20 then 1 else 0 end) / count(*), 1) as blowout_pct
        from main_intermediate.int_games_enriched
        group by season_start_year order by season_start_year
    """)

    fig2 = px.area(drama, x="season", y=["clutch_pct", "blowout_pct", "ot_pct"],
                   title="Game Drama: Clutch (≤5pt) vs Blowouts (20+) vs OT")
    st.plotly_chart(fig2, use_container_width=True)

    home = query("""
        select s.season_display as season,
               round(100.0 * sum(case when g.is_home_team_winner then 1 else 0 end) / count(*), 1) as home_win_pct
        from main_marts.fct_game_results g
        left join main_marts.dim_seasons s on g.season_key = s.season_key
        group by s.season_display order by s.season_display
    """)

    fig3 = px.line(home, x="season", y="home_win_pct",
                   title="Home Court Advantage Over Time", markers=True)
    fig3.update_layout(yaxis_range=[40, 70])
    st.plotly_chart(fig3, use_container_width=True)
