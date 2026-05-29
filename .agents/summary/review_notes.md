# Review Notes

## Consistency Check ✅

### Cross-Document Alignment

| Check | Status | Notes |
|-------|--------|-------|
| Model counts match across docs | ✅ | 10 staging, 4 intermediate, 7 dimensions, 6 facts — consistent in architecture.md, components.md, index.md |
| Technology versions consistent | ✅ | dbt_utils 1.3.1, DuckDB 1.3.0, Streamlit 1.45.1, Plotly 6.1.2 — matches source files |
| Schema names consistent | ✅ | staging, intermediate, marts — matches dbt_project.yml config |
| Seed names consistent | ✅ | team_maps, arena_maps, team_abbreviation_mappings — matches filesystem |
| Materialization strategy consistent | ✅ | views/tables/incremental — matches dbt_project.yml |
| Pipeline selector tags consistent | ✅ | staging, intermediate, dimension, fact, marts — matches selectors.yml |

### Terminology Consistency

| Term | Usage | Status |
|------|-------|--------|
| "team_maps" vs "team_mappings" | Both CSV files exist; `team_maps.csv` is the primary seed used in models, `team_mappings.csv` is supplementary | ✅ Documented correctly |
| "arena_maps" vs "arena_mappings" | Both exist; `arena_maps.csv` is used in models | ✅ Documented correctly |
| Schema prefixes | `main_marts`, `main_intermediate` used in Streamlit queries | ✅ Consistent with DuckDB schema naming |

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

### Gaps Identified

| Gap | Severity | Recommendation |
|-----|----------|----------------|
| No documentation of `stg_season_thresholds` / `stg_team_season_thresholds` internal logic | Low | These models derive statistical thresholds for tiering; SQL could be documented for maintainability |
| Evidence BI page content (`reports/pages/index.md`) not detailed | Low | The Evidence dashboard layout and specific visualizations are not enumerated |
| Streamlit app pages 2-7 logic not fully documented | Low | Only page 1 (Overview) was read in detail; other pages follow similar patterns |
| No documentation of `fct_quarter_scoring` or `fct_player_shots` column details | Medium | These fact tables lack column-level documentation in data_models.md |
| No test coverage documentation | Low | Tests are defined in schema.yml but test strategy could be more explicit |
| No data freshness/volume expectations documented | Low | No SLA or expected row counts documented |
| `deleted_at` filter in stg_games not explained | Low | Source data has soft-delete pattern; could document data quality assumptions |

### Language Support Limitations

- **SQL/Jinja**: Fully analyzed — all dbt models parsed and documented
- **Python**: Partially analyzed — Streamlit app structure documented, but internal page logic (pages 2-7) summarized rather than fully detailed
- **JavaScript/Node.js**: Evidence BI config documented; internal Evidence framework not analyzed (third-party tool)
- **YAML**: All configuration files fully analyzed

## Recommendations

1. **Add column-level docs for `fct_quarter_scoring` and `fct_player_shots`** — These are the two fact tables without detailed column listings in data_models.md
2. **Document the tiering logic** — `stg_season_thresholds` and `stg_player_game_adv_stats_extended` contain dynamic percentile-based tiering that is a key differentiator of this project
3. **Add data quality assumptions** — Document the `deleted_at IS NULL` filter and any other data quality gates
4. **Consider adding a glossary** — Terms like "four factors", "net rating", "usage rate" have specific basketball analytics meanings
