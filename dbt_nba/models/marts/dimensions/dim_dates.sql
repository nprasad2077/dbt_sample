{{
    config(
        materialized='table',
        schema='marts',
        tags=["dimension"]
    )
}}

{% set start_date_query %}
select min(game_date)::date from {{ ref('stg_games') }}
{% endset %}
{% set start_date = dbt_utils.get_single_value(start_date_query) %}

{% set end_date_query %}
select max(game_date)::date from {{ ref('stg_games') }}
{% endset %}
{% set end_date = dbt_utils.get_single_value(end_date_query) %}

WITH date_spine AS (
    SELECT UNNEST(generate_series(
        '{{ start_date }}'::date,
        '{{ end_date }}'::date,
        INTERVAL '1 day'
    ))::date AS date_day
)

SELECT
    CAST(strftime(date_day, '%Y%m%d') AS INTEGER) AS date_key,
    date_day AS full_date,
    EXTRACT(YEAR FROM date_day)::int AS year,
    EXTRACT(QUARTER FROM date_day)::int AS quarter_of_year,
    EXTRACT(MONTH FROM date_day)::int AS month_of_year,
    strftime(date_day, '%B') AS month_name,
    EXTRACT(DAY FROM date_day)::int AS day_of_month,
    EXTRACT(ISODOW FROM date_day)::int AS day_of_week,
    strftime(date_day, '%A') AS day_of_week_name,
    EXTRACT(DOY FROM date_day)::int AS day_of_year,
    EXTRACT(WEEK FROM date_day)::int AS week_of_year,
    CASE
        WHEN EXTRACT(ISODOW FROM date_day) IN (6, 7) THEN true
        ELSE false
    END AS is_weekend
FROM date_spine
ORDER BY full_date
