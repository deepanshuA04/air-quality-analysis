# Urban Air Quality Trend & Policy Impact Analysis (CPCB)

[![CI](https://github.com/deepanshuA04/air-quality-analysis/actions/workflows/ci.yml/badge.svg)](https://github.com/deepanshuA04/air-quality-analysis/actions/workflows/ci.yml)

Analysis of hourly Central Pollution Control Board (CPCB) air-quality readings
across 8 Indian cities: data cleaning, time-series trend analysis, and
before/after hypothesis testing of real policy interventions, with a SQL layer
and a Power BI monitoring dashboard.

## Dataset

| | |
|---|---|
| Source | [Air Quality Data in India (2015 - 2020)](https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india) by rohanrao on Kaggle, compiled from CPCB's public monitoring network |
| Files used | `city_hour.csv` (hourly, city-level), `city_day.csv` (daily, cross-check only), `stations.csv` (station metadata) |
| Download date | 2026-08-12 |
| License | CC0-1.0 (public domain) |
| Reproducing the download | `uv run python scripts/download_data.py` (requires a Kaggle API token; see [Kaggle API docs](https://www.kaggle.com/docs/api)). Downloaded files are checksummed against `data/raw/CHECKSUMS.sha256`. |

### Coverage vs. the original plan

The project was scoped assuming 2019-2024 coverage. The real dataset's hourly
city-level file (`city_hour.csv`) covers **2015-01-01 to 2020-07-01** — it
stops before 2024 because CPCB's own aggregation (and the Kaggle mirror of
it) ends there. The date range below reflects what the data actually
contains, not the original plan.

Of 26 cities in the raw file, coverage length and completeness vary widely
(full 2015-2020 span in some, a few months in others — see the
`stations.csv`/`city_hour.csv` breakdown reproduced by
`scripts/build_quality_profile.py`). The 8 cities selected for this analysis
are the largest metros with the longest usable time series, giving both
geographic spread and enough pre/post history for the intervention analysis:

**Delhi, Mumbai, Kolkata, Chennai, Bengaluru, Hyderabad, Ahmedabad, Lucknow**

| City | Hourly rows | Date range | PM2.5 completeness |
|---|---|---|---|
| Delhi | 48,192 | 2015-01-01 → 2020-07-01 | 99.2% |
| Mumbai | 48,192 | 2015-01-01 → 2020-07-01 | 37.7% |
| Chennai | 48,192 | 2015-01-01 → 2020-07-01 | 93.1% |
| Bengaluru | 48,192 | 2015-01-01 → 2020-07-01 | 90.4% |
| Ahmedabad | 48,192 | 2015-01-01 → 2020-07-01 | 64.6% |
| Lucknow | 48,192 | 2015-01-01 → 2020-07-01 | 93.4% |
| Hyderabad | 48,107 | 2015-01-04 → 2020-07-01 | 92.5% |
| Kolkata | 19,503 | 2018-04-10 → 2020-07-01 | 92.6% |

Across these 8 cities, the raw file contains **356,762 city-hour rows** and,
melted to one row per city-hour-pollutant (12 pollutants tracked), **~3.26
million non-null pollutant readings** — above the originally planned 1.2M+,
just over a shorter and earlier window (Jan 2015-Jul 2020) than 2019-2024.
Kolkata's monitoring only starts in April 2018 and is analyzed on its
available window rather than padded or excluded.

**Resume bullet, updated to match reality:** *Analyzed 3.2M+ hourly pollutant
readings from 8 Indian cities (2015-2020), cleaning missing and out-of-range
sensor values using interpolation and outlier rules.*

## Data-quality profile (before any cleaning)

Computed by `uv run python scripts/build_quality_profile.py` on the raw
tidy long-format frame (8 cities × 12 pollutants × hourly), before any
cleaning rule runs. Full detail is written to `reports/quality_profile_full.csv`
(540 city × pollutant × year rows); summaries below.

**By city** (across all 12 pollutants and all years in that city's window):

| City | Expected hours | Non-null readings | % missing | Impossible values |
|---|---|---|---|---|
| Delhi | 578,304 | 549,490 | 4.98% | 0 |
| Hyderabad | 577,284 | 536,842 | 7.01% | 0 |
| Kolkata | 234,036 | 216,260 | 7.60% | 0 |
| Bengaluru | 578,304 | 475,666 | 17.75% | 0 |
| Chennai | 578,304 | 445,889 | 22.90% | 0 |
| Lucknow | 578,304 | 420,409 | 27.30% | 0 |
| Ahmedabad | 578,304 | 329,690 | 42.99% | 2,978 (0.90% of readings, all CO) |
| Mumbai | 578,304 | 286,080 | 50.53% | 0 |

**By pollutant** (across all 8 cities and all years): PM10 (51.9% missing)
and Xylene (60.5% missing) are the least-covered pollutants; CO, NOx, and
Benzene are the best-covered (9-13% missing). PM2.5, the headline pollutant
for this project, is 17.8% missing overall.

**Impossible values found:** only in CO, and only in Ahmedabad — 2,978
readings (0.9% of Ahmedabad's CO readings) above the 50 mg/m³ plausibility
ceiling (see `config.PLAUSIBLE_CEILING`; CPCB's 24h CO standard is 2 mg/m³,
so ambient readings above 50 mg/m³ indicate an instrument fault, not real
air). No negative values and no exact-zero PM2.5/PM10 readings were present
in this source file — the zero-is-impossible rule is implemented and unit
tested but doesn't trigger on this particular dataset.

**A miss worth flagging:** Mumbai's PM2.5 sensor reports **zero readings
for all of 2015-2017** (100% missing those years), only starting in 2018 —
this is why Mumbai's overall PM2.5 completeness (37.7%, see the coverage
table above) is so much lower than its peers despite having a full
2015-2020 row span. This is a real station-startup gap, not a bug, and is
preserved rather than backfilled with fabricated pre-2018 values.

### Cleaning rules

| Rule | Function | Justification |
|---|---|---|
| Impossible values → missing | `cleaning.flag_impossible_values` | Negative concentrations are not physically possible; values above a documented per-pollutant ceiling (see `config.PLAUSIBLE_CEILING`) indicate an instrument fault, not a real reading; exact-zero PM2.5/PM10 indicates the particulate sensor was off (ambient PM is never truly zero) — restricted to PM2.5/PM10 because gaseous pollutants legitimately read zero near their detection limit. |
| Short gaps (≤6h) → interpolated | `cleaning.interpolate_short_gaps` | A sensor dropout of a few hours is well-approximated by linear interpolation between the readings on either side of the gap. |
| Long gaps (>6h) → left missing | `cleaning.interpolate_short_gaps` | Interpolating a multi-day or multi-week outage would invent data with no basis — these are left as `NaN` with a `missing_long_gap` quality flag rather than filled in. |
| Outliers → flagged, not dropped | `cleaning.flag_outliers_iqr` | IQR fences computed **per city, per pollutant, per calendar month** (not a single global threshold) — Delhi winter PM2.5 routinely runs 300-900 µg/m³, which a global fence would flag as an outlier on every winter night. A per-month fence lets each city's own seasonal baseline define what's unusual for that city in that season. Flagged values are kept (with a flag) rather than removed, since "unusual for this city-month" is not the same as "wrong." |

## Reproducing this analysis

```bash
uv sync --frozen
uv run python scripts/download_data.py           # fetch raw CSVs (needs Kaggle credentials)
uv run python scripts/build_quality_profile.py    # pre-cleaning data-quality profile -> reports/
# further pipeline steps (cleaning, SQL load, EDA, stats) are added as the
# project progresses — see milestones below.
```

## Project status

- [x] Milestone 1 — scaffold, CI, dataset sourcing decision
- [x] Milestone 2 — data-quality profile
- [ ] Milestone 3 — cleaning pipeline + SQLite load
- [ ] Milestone 4 — SQL views
- [ ] Milestone 5 — time-series EDA
- [ ] Milestone 6 — hypothesis testing (t-tests, ANOVA) + honesty section
- [ ] Milestone 7 — Power BI dashboard
- [ ] Milestone 8 — findings & limitations write-up
