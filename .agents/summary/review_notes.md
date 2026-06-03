# Review Notes

## Consistency Check ✅

### Cross-Document Alignment

| Check | Status | Notes |
|-------|--------|-------|
| Model counts match across docs | ✅ | 10 staging, 4 intermediate, 7 dimensions, 6 facts — consistent across architecture.md, components.md, index.md, dependencies.md |
| Technology versions consistent | ✅ | dbt_utils 1.3.1, DuckDB >=1.3.0, Streamlit >=1.45.1, Plotly >=6.1.2 — matches pyproject.toml |
| Schema names consistent | ✅ | staging, intermediate, marts — matches dbt_project.yml config |
| Seed names consistent | ✅ | team_maps, arena_maps, team_abbreviation_mappings, arena_mappings, team_mappings — matches filesystem |
| Materialization strategy consistent | ✅ | views/tables/incremental — matches dbt_project.yml |
| Pipeline selector tags consistent | ✅ | staging, intermediate, dimension, fact, marts — matches selectors.yml |
| CI/CD workflow details consistent | ✅ | Daily 06:00 UTC, uv setup, DuckDB CLI — matches .github/workflows/pipeline.yml |
| Dependency graph consistent | ✅ | int_games_enriched depends on int_team_performance — verified in SQL source |
| DB path consistent | ✅ | `../data/DB/dbt_nba.duckdb` in profiles.yml; Streamlit/Evidence use reports copy |
| Python version constraint | ✅ | >=3.11, <3.13 — matches pyproject.toml |

### Terminology Consistency

| Term | Usage | Status |
|------|-------|--------|
| "team_maps" vs "team_mappings" | Both CSV files exist; `team_maps.csv` is the primary seed used in models, `team_mappings.csv` is supplementary | ✅ Documented correctly |
| "arena_maps" vs "arena_mappings" | Both exist; `arena_maps.csv` is used in models | ✅ Documented correctly |
| Schema prefixes | `main_marts`, `main_intermediate`, `main_staging` in query consumers | ✅ Consistent with DuckDB schema naming |
| Package manager | `uv` consistently referenced as the Python package manager | ✅ |

## Completeness Check

### Well-Documented Areas ✅

- [x] Layer architecture and materialization strategy
- [x] All model names and their responsibilities
- [x] Star schema relationships and surrogate key pattern
- [x] Incremental strategy with 30-day lookback
- [x] Team abbreviation conforming pattern
- [x] Pipeline execution commands and selectors
- [x] Reporting architecture (Evidence + Streamlit)
- [x] Configuration variables and their purposes
- [x] Source table contracts and key constraints
- [x] CI/CD pipeline (GitHub Actions)
- [x] Extraction flow (Postgres → DuckDB)
- [x] All 6 fact table column details
- [x] Dimension table schemas
- [x] Dynamic tiering pattern
- [x] Full dependency DAG

### Gaps Identified

| Gap | Severity | Recommendation |
|-----|----------|----------------|
| No schema YAML for marts layer (dims/facts) | Medium | Create `models/marts/_marts_models.yml` with unique/not_null tests for all dimension and fact tables |
| `stg_season_thresholds` internal percentile logic not detailed | Low | Document which columns and percentile breakpoints are computed |
| Evidence BI page layout not fully documented | Low | The Evidence dashboard visualizations and chart types could be enumerated |
| Streamlit pages 2-7 detailed query logic | Low | Each page's specific SQL queries and chart configurations are summarized but not exhaustive |
| No data freshness/volume expectations | Low | Document expected row counts or data SLA for monitoring |
| `deleted_at` filter in stg_games not fully explained | Low | Document soft-delete pattern assumption from upstream Postgres |
| No error handling in pipeline.sh beyond POSTGRES_URL check | Low | Pipeline has no retry logic or failure notification |
| `team_abbreviation_mappings.csv` and `team_mappings.csv` usage unclear | Low | Document whether these seeds are referenced by any models or are lookup-only |

### Language Support Coverage

| Language | Analysis Depth | Notes |
|----------|---------------|-------|
| SQL/Jinja | Full | All 27 dbt models parsed and documented with column-level detail |
| Python | High | Streamlit app structure, imports, page logic documented |
| YAML | Full | All configuration files (dbt_project, profiles, selectors, packages, schema, models) analyzed |
| Shell | Full | pipeline.sh and extract.sql fully documented |
| JavaScript/Node.js | Low | Evidence BI is third-party framework; only SQL queries and config documented |

## Recommendations

1. **Create marts schema YAML** — Add `_marts_models.yml` with unique_key tests for all fact tables and not_null for dimension PKs
2. **Document `team_mappings.csv` and `team_abbreviation_mappings.csv` usage** — Clarify if these seeds are consumed by any model or are reference-only
3. **Add pipeline failure alerting** — Consider adding Slack/email notification on CI failure
4. **Document data quality gates** — Formalize the `deleted_at IS NULL` and `did_play = TRUE` patterns as explicit data contracts
5. **Consider adding dbt freshness checks** — `loaded_at_field` on sources would catch stale data
