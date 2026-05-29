# dbt_nba Documentation Index

> **For AI Assistants**: This file is the primary entry point for understanding the dbt_nba codebase. Read this file first to determine which detailed documentation files to consult for specific questions.

## Quick Reference

- **Project**: NBA analytics data warehouse (dbt + DuckDB → star schema → dashboards)
- **Stack**: dbt-duckdb, dbt_utils, Evidence BI, Streamlit, Plotly
- **Architecture**: 3-layer pipeline (staging views → intermediate tables → incremental mart facts + dimension tables)
- **Data**: 7 raw NBA tables → 10 staging → 4 intermediate → 7 dimensions + 6 facts

## Documentation Map

| File | Purpose | Consult When... |
|------|---------|-----------------|
| [codebase_info.md](codebase_info.md) | Project identity, tech stack, directory structure, config variables, source tables | You need project overview, directory layout, or configuration details |
| [architecture.md](architecture.md) | System design, layer patterns, materialization strategy, reporting architecture | You need to understand how components connect, why design decisions were made, or how data flows |
| [components.md](components.md) | Detailed listing of all models, seeds, and reporting components with responsibilities | You need to find a specific model, understand what it does, or identify which component handles a concern |
| [interfaces.md](interfaces.md) | Database connections, source contracts, cross-layer references, query interfaces, pipeline selectors | You need to understand how systems connect, what schemas are used, or how to execute the pipeline |
| [data_models.md](data_models.md) | Star schema ER diagram, fact table columns, dimension details, shot zones, archetypes | You need column-level detail, understand relationships between tables, or work with specific metrics |
| [workflows.md](workflows.md) | Pipeline execution, incremental refresh, data transformation flows, development workflow | You need to run the pipeline, add new models, understand transformation logic, or debug data flow |
| [dependencies.md](dependencies.md) | External packages, Python deps, internal model dependency graph | You need to understand what packages are used, add dependencies, or trace model lineage |

## Key Concepts

### Layered Architecture
- **Staging**: 1:1 with source tables. Cleans, filters, derives basic metrics. Materialized as views.
- **Intermediate**: Joins across entities, conforms team abbreviations via temporal seed mappings. Materialized as tables.
- **Marts**: Star schema. Dimensions are full-rebuild tables. Facts are incremental with 30-day lookback.

### Team Abbreviation Conforming
Team names change over time. The `team_maps` seed has `start_year`/`end_year` columns. All intermediate models join on both abbreviation AND season year range to get the correct historical mapping.

### Incremental Strategy
Fact tables use `unique_key` + 30-day lookback: `WHERE game_date >= MAX(game_date) - 30 days`. This handles late-arriving data without full rebuilds.

### Reporting Consumers
Two independent dashboards read from the same DuckDB:
- **Evidence BI** (Node.js) — SQL-in-markdown declarative dashboards
- **Streamlit** (Python) — Interactive multi-page app with Plotly charts

## Common Tasks

| Task | Start Here |
|------|-----------|
| Add a new staging model | [workflows.md](workflows.md) → Development Workflow |
| Understand a specific model's columns | [data_models.md](data_models.md) |
| Find what feeds a fact table | [dependencies.md](dependencies.md) → Internal Model Dependencies |
| Run the pipeline | [interfaces.md](interfaces.md) → Pipeline Execution Interface |
| Add a new dashboard page | [components.md](components.md) → Reporting Components |
| Understand the star schema | [data_models.md](data_models.md) → Star Schema Overview |
| Debug team name mismatches | [architecture.md](architecture.md) → Team Abbreviation Conforming |
