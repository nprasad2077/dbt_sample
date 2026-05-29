-- Extract source tables from Postgres into DuckDB
-- Requires: POSTGRES_URL environment variable
-- Usage: Run via scripts/pipeline.sh (handles variable substitution)

INSTALL postgres;
LOAD postgres;

ATTACH '${POSTGRES_URL}' AS pg (TYPE POSTGRES, READ_ONLY);

DROP TABLE IF EXISTS main.games;
DROP TABLE IF EXISTS main.line_scores;
DROP TABLE IF EXISTS main.player_game_basic_stats;
DROP TABLE IF EXISTS main.player_game_adv_stats;
DROP TABLE IF EXISTS main.player_shot_charts;
DROP TABLE IF EXISTS main.team_game_basic_stats;
DROP TABLE IF EXISTS main.team_game_adv_stats;

CREATE TABLE main.games AS SELECT * FROM pg.public.games;
CREATE TABLE main.line_scores AS SELECT * FROM pg.public.line_scores;
CREATE TABLE main.player_game_basic_stats AS SELECT * FROM pg.public.player_game_basic_stats;
CREATE TABLE main.player_game_adv_stats AS SELECT * FROM pg.public.player_game_adv_stats;
CREATE TABLE main.player_shot_charts AS SELECT * FROM pg.public.player_shot_charts;
CREATE TABLE main.team_game_basic_stats AS SELECT * FROM pg.public.team_game_basic_stats;
CREATE TABLE main.team_game_adv_stats AS SELECT * FROM pg.public.team_game_adv_stats;

DETACH pg;

SELECT 'Extraction complete' AS status;
