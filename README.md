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

## Reproducing this analysis

```bash
uv sync --frozen
uv run python scripts/download_data.py       # fetch raw CSVs (needs Kaggle credentials)
# further pipeline steps (profiling, cleaning, SQL load, EDA, stats) are added
# as the project progresses — see milestones below.
```

## Project status

- [x] Milestone 1 — scaffold, CI, dataset sourcing decision
- [ ] Milestone 2 — data-quality profile
- [ ] Milestone 3 — cleaning pipeline + SQLite load
- [ ] Milestone 4 — SQL views
- [ ] Milestone 5 — time-series EDA
- [ ] Milestone 6 — hypothesis testing (t-tests, ANOVA) + honesty section
- [ ] Milestone 7 — Power BI dashboard
- [ ] Milestone 8 — findings & limitations write-up
