-- SQL views over the `readings` table (city, datetime, pollutant, value,
-- quality_flag) loaded by scripts/clean_and_load.py. Views are dropped and
-- recreated so this script is safe to re-run (db.apply_sql_views does so
-- after every load).
--
-- `value` is NULL for quality_flag = 'missing_long_gap'; SQLite's AVG/COUNT
-- ignore NULLs, so aggregates below correctly exclude those hours without
-- any extra filtering. 'outlier_seasonal' and 'interpolated' readings are
-- genuine/estimated values and are included in averages like any other
-- reading.

DROP VIEW IF EXISTS v_city_pollutant_daily;
DROP VIEW IF EXISTS v_city_pollutant_daily_rolling30;
DROP VIEW IF EXISTS v_city_pollutant_monthly;
DROP VIEW IF EXISTS v_city_pollutant_monthly_mom;
DROP VIEW IF EXISTS v_city_monthly_profile;
DROP VIEW IF EXISTS v_pm25_exceedance_days;
DROP VIEW IF EXISTS v_pm25_exceedance_summary;

-- One row per city + pollutant + calendar date. A day's average requires
-- at least 18 of its 24 hourly readings (75%) to be non-null; days with
-- sparser coverage are reported as NULL rather than averaged from a
-- handful of hours, which would silently bias the daily figure toward
-- whichever few hours happened to be measured.
CREATE VIEW v_city_pollutant_daily AS
SELECT
    city,
    pollutant,
    date(datetime) AS date,
    COUNT(value) AS n_readings,
    CASE WHEN COUNT(value) >= 18 THEN ROUND(AVG(value), 3) END AS avg_value
FROM readings
GROUP BY city, pollutant, date(datetime);

-- 30-day trailing rolling average of the daily series above. Because
-- v_city_pollutant_daily has exactly one row per calendar date (even when
-- avg_value is NULL), a 30-row window is a true 30-calendar-day window.
CREATE VIEW v_city_pollutant_daily_rolling30 AS
SELECT
    city,
    pollutant,
    date,
    avg_value,
    ROUND(
        AVG(avg_value) OVER (
            PARTITION BY city, pollutant
            ORDER BY date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ),
        3
    ) AS rolling_30d_avg
FROM v_city_pollutant_daily;

-- One row per city + pollutant + calendar month (year-month), from the
-- daily view so it inherits the same >=18h/day completeness rule.
CREATE VIEW v_city_pollutant_monthly AS
SELECT
    city,
    pollutant,
    strftime('%Y', date) AS year,
    strftime('%m', date) AS month,
    strftime('%Y-%m', date) AS year_month,
    COUNT(avg_value) AS n_days_with_data,
    ROUND(AVG(avg_value), 3) AS avg_value
FROM v_city_pollutant_daily
GROUP BY city, pollutant, strftime('%Y-%m', date);

-- Month-over-month change, via LAG over the monthly series.
CREATE VIEW v_city_pollutant_monthly_mom AS
SELECT
    city,
    pollutant,
    year,
    month,
    year_month,
    avg_value,
    LAG(avg_value) OVER (PARTITION BY city, pollutant ORDER BY year_month) AS prev_month_avg,
    ROUND(
        avg_value - LAG(avg_value) OVER (PARTITION BY city, pollutant ORDER BY year_month),
        3
    ) AS mom_change
FROM v_city_pollutant_monthly;

-- Seasonal profile: average by calendar month (1-12), pooled across all
-- years in that city's window — the empirical basis for identifying the
-- high-risk window, rather than assuming Oct-Jan.
CREATE VIEW v_city_monthly_profile AS
SELECT
    city,
    pollutant,
    CAST(strftime('%m', date) AS INTEGER) AS calendar_month,
    COUNT(avg_value) AS n_days_with_data,
    ROUND(AVG(avg_value), 3) AS avg_value,
    ROUND(MIN(avg_value), 3) AS min_daily_avg,
    ROUND(MAX(avg_value), 3) AS max_daily_avg
FROM v_city_pollutant_daily
GROUP BY city, pollutant, CAST(strftime('%m', date) AS INTEGER);

-- Per-city-day PM2.5 exceedance flag against the CPCB 24h standard
-- (60 ug/m3; see config.CPCB_PM25_24H_STANDARD).
CREATE VIEW v_pm25_exceedance_days AS
SELECT
    city,
    date,
    avg_value AS pm25_daily_avg,
    CASE WHEN avg_value > 60 THEN 1 ELSE 0 END AS is_exceedance
FROM v_city_pollutant_daily
WHERE pollutant = 'PM2.5' AND avg_value IS NOT NULL;

-- City-level exceedance-day summary (count and % of valid days).
CREATE VIEW v_pm25_exceedance_summary AS
SELECT
    city,
    COUNT(*) AS n_valid_days,
    SUM(is_exceedance) AS n_exceedance_days,
    ROUND(100.0 * SUM(is_exceedance) / COUNT(*), 2) AS pct_exceedance_days
FROM v_pm25_exceedance_days
GROUP BY city;
