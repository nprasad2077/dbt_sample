# Workflows

## Pipeline Execution

### Full Build (Local)

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant dbt as dbt CLI
    participant DB as DuckDB

    Dev->>dbt: dbt deps --profiles-dir .
    dbt->>dbt: Install dbt_utils 1.3.1

    Dev->>dbt: dbt seed --profiles-dir .
    dbt->>DB: Load team_maps, arena_maps, etc.

    Dev->>dbt: dbt build --profiles-dir .
    dbt->>DB: Create staging views (10)
    dbt->>DB: Create intermediate tables (4)
    dbt->>DB: Create dimension tables (7)
    dbt->>DB: Create/update fact tables (6, incremental)
    dbt->>dbt: Run tests (unique, not_null, accepted_values)
    dbt-->>Dev: Build complete
```

### CI/CD Pipeline (GitHub Actions)

```mermaid
sequenceDiagram
    participant GH as GitHub Actions
    participant PG as Postgres (remote)
    participant DB as DuckDB
    participant dbt as dbt CLI

    Note over GH: Triggered daily 06:00 UTC or manual
    GH->>GH: Checkout repo (with LFS)
    GH->>GH: Setup uv + DuckDB CLI
    GH->>PG: extract.sql (DuckDB Postgres extension)
    PG-->>DB: 7 tables created in data/DB/dbt_nba.duckdb
    GH->>dbt: dbt deps + dbt build
    dbt->>DB: Full pipeline execution
    GH->>GH: Copy DB to reports/sources/nba/
    GH->>GH: git commit + push updated .duckdb files
```

### Extraction Flow

```mermaid
flowchart TD
    A[pipeline.sh starts] --> B{POSTGRES_URL set?}
    B -->|No| C[Error: exit]
    B -->|Yes| D[Delete existing dbt_nba.duckdb]
    D --> E[Run extract.sql via DuckDB CLI]
    E --> F[INSTALL postgres extension]
    F --> G[ATTACH Postgres as read-only]
    G --> H[CREATE OR REPLACE 7 tables]
    H --> I[DETACH Postgres]
    I --> J[dbt deps + dbt build]
    J --> K[Copy DB to reports/sources/nba/]
```

### Incremental Refresh

```mermaid
flowchart TD
    A[dbt build --profiles-dir .] --> B{Is incremental model?}
    B -->|No| C[Full rebuild]
    B -->|Yes| D[Check existing data]
    D --> E[Find MAX game_date]
    E --> F[Process records from MAX - 30 days]
    F --> G[Merge on unique_key]
```

### Selector-Based Execution

```mermaid
flowchart LR
    A[nba_pipeline selector] --> B[tag:staging]
    A --> C[tag:intermediate]
    A --> D[tag:dimension]
    A --> E[tag:fact]
    B --> F[10 staging views]
    C --> G[4 intermediate tables]
    D --> H[7 dimension tables]
    E --> I[6 fact tables]
```

## Data Transformation Flow

### Team Abbreviation Conforming

```mermaid
flowchart TD
    A[Raw team abbreviation<br/>e.g. 'SEA'] --> B[Join team_maps seed]
    B --> C{season_start_year<br/>BETWEEN start_year AND end_year?}
    C -->|Yes| D[Conformed to current name<br/>e.g. 'OKC']
    C -->|No| E[No match / data quality issue]
```

### Player Performance Enrichment

```mermaid
flowchart TD
    A[stg_player_game_basic_stats] --> D[int_player_performance]
    B[stg_player_game_adv_stats_extended] --> D
    C[stg_games] --> D
    E[team_maps seed] --> D
    D --> F[Unified player × game record]
    F --> G{Archetype classification}
    G --> H[usage_tier + impact_tier + efficiency_tier]
    H --> I[dim_player_game_archetypes]
    F --> J[fct_player_game_stats]
```

### Shot Data Unification

```mermaid
flowchart TD
    A[stg_player_shot_charts<br/>Field goal attempts<br/>shot_source='shot_chart'] --> C[int_player_shots_enriched]
    B[stg_player_game_basic_stats<br/>Free throw attempts derived<br/>shot_source='box_score_ft'] --> C
    C --> D[Unified shot-level dataset<br/>with has_game_match filter]
    D --> E[fct_player_shots<br/>Individual shots]
    D --> F[fct_player_game_shooting<br/>Aggregated per game]
```

### Dynamic Tiering

```mermaid
flowchart TD
    A[stg_player_game_basic_stats] --> B[stg_season_thresholds]
    B --> C[Per-season percentile breakpoints<br/>for usage, impact, efficiency]
    C --> D[stg_player_game_adv_stats_extended]
    D --> E[Dynamic tier assignments<br/>that adjust per season]
```

## Development Workflow

### Adding a New Model

1. Create SQL file in appropriate layer directory (`models/staging/`, `models/intermediate/`, or `models/marts/`)
2. Add model definition to relevant YAML (`models/schema.yml` for staging, `models/intermediate/_int_models.yml` for intermediate)
3. Tags are applied automatically via directory config in `dbt_project.yml`
4. Run `dbt build --profiles-dir . --select model_name` to test
5. Update Evidence/Streamlit queries if the model feeds reporting
6. **Note**: No schema YAML exists for marts; tests for dimensions/facts should be added to a new `_marts_models.yml`

### Testing Strategy

- **Source tests**: `unique` and `not_null` on primary/foreign keys in `schema.yml`
- **Model tests**: `unique`, `not_null`, `accepted_values` on key columns
- **Intermediate tests**: `dbt_utils.unique_combination_of_columns` for composite keys
- **Configuration**: `severity: warn`, `store_failures: true` (results stored in `test_results` schema)
- **Gap**: Mart models (dimensions/facts) have no schema YAML or explicit tests

### Running with uv

All dbt commands should be run via `uv run` from the `dbt_nba/` directory:
```bash
uv run --project .. dbt build --profiles-dir .
uv run --project .. dbt test --profiles-dir .
```

## Reporting Refresh

### Evidence BI

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant dbt as dbt
    participant EV as Evidence

    Dev->>dbt: dbt build (updates marts)
    Note over dbt: DuckDB file updated
    Dev->>EV: npm run dev (in reports/)
    EV->>EV: Reads dbt_nba.duckdb copy
    EV->>EV: Executes 12 SQL sources
    EV-->>Dev: Dashboard at localhost
```

### Streamlit

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant ST as Streamlit

    Dev->>ST: streamlit run streamlit_app/app.py
    ST->>ST: Connect DuckDB (read-only)
    ST->>ST: Cache queries with @st.cache_data
    ST-->>Dev: Dashboard at :8501
```

Note: Streamlit reads from the reports copy (`dbt_nba/reports/sources/nba/dbt_nba.duckdb`), so the DB must be copied after dbt build (the pipeline script does this automatically).
