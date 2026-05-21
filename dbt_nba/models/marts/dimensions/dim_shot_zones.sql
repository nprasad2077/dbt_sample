{{
    config(
        materialized='table',
        schema='marts',
        tags=["dimension"]
    )
}}

WITH zones AS (
    SELECT * FROM (
        VALUES
            ('At Rim (0-3 ft)',           0,  3,  1, 'Paint',      'Interior',    'Field Goal'),
            ('Short Range (4-10 ft)',     4,  10, 2, 'Paint',      'Interior',    'Field Goal'),
            ('Mid Range (11-16 ft)',      11, 16, 3, 'Mid Range',  'Mid Range',   'Field Goal'),
            ('Long Mid Range (17-23 ft)', 17, 23, 4, 'Mid Range',  'Mid Range',   'Field Goal'),
            ('Three Point (24-27 ft)',    24, 27, 5, 'Perimeter',  'Three Point', 'Field Goal'),
            ('Deep Three (28+ ft)',       28, 50, 6, 'Perimeter',  'Three Point', 'Field Goal'),
            ('Free Throw (15 ft)',        15, 15, 7, 'Free Throw', 'Free Throw',  'Free Throw')
    ) AS t(shot_distance_zone, min_distance_ft, max_distance_ft, zone_order, zone_group, zone_category, shot_class)
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['shot_distance_zone']) }} AS shot_zone_key,
    shot_distance_zone,
    min_distance_ft,
    max_distance_ft,
    zone_order,
    zone_group,
    zone_category,
    shot_class
FROM zones
ORDER BY zone_order
