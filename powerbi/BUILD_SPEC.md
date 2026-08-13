# Power BI build spec

Exact steps to build the 3-page dashboard from `powerbi/data/*.csv`. Follow
in order — each step assumes the previous ones are done. Aim: a real star
schema (fact tables + a Date dimension + a City dimension), not 9 flat
CSVs dropped on a canvas.

## 1. Import and shape (Power Query)

Open Power BI Desktop → **Get Data → Text/CSV**, import each file from
`powerbi/data/`:

- `v_city_pollutant_daily.csv`
- `v_city_pollutant_daily_rolling30.csv`
- `v_city_monthly_profile.csv`
- `v_pm25_exceedance_summary.csv`
- `grap_before_after.csv`
- `anova_pm25_group_means.csv`

(`v_city_pollutant_monthly.csv`, `v_city_pollutant_monthly_mom.csv`, and
`v_pm25_exceedance_days.csv` aren't used by the 3 pages below — skip them
unless you add a page that needs month-over-month or day-level exceedance
detail.)

In Power Query (**Transform Data**), for each table:
- Set `date` to Date type, `city`/`pollutant`/`status` to Text, numeric
  columns to Decimal Number.
- Rename tables with a `Fact_` prefix: `Fact_Daily`, `Fact_Rolling30`,
  `Fact_MonthlyProfile`, `Fact_Exceedance`, `Fact_GRAP`, `Fact_ANOVA`.

## 2. Build the Date dimension

**Modeling → New Table**, on any table:

```
Dim_Date =
ADDCOLUMNS(
    CALENDAR(DATE(2015,1,1), DATE(2020,7,1)),
    "Year", YEAR([Date]),
    "MonthNum", MONTH([Date]),
    "MonthName", FORMAT([Date], "MMM"),
    "IsWinterMonth", MONTH([Date]) IN {10, 11, 12, 1, 2}
)
```

**Mark as date table**: select `Dim_Date` → Table tools → Mark as Date
Table → column `Date`.

## 3. Build the City dimension

**Modeling → New Table**:

```
Dim_City =
DATATABLE(
    "City", STRING, "Region", STRING, "GRAP_Applicable", BOOLEAN,
    {
        {"Delhi", "North", TRUE},
        {"Lucknow", "North", FALSE},
        {"Kolkata", "East", FALSE},
        {"Mumbai", "West", FALSE},
        {"Ahmedabad", "West", FALSE},
        {"Chennai", "South", FALSE},
        {"Bengaluru", "South", FALSE},
        {"Hyderabad", "South", FALSE}
    }
)
```

`GRAP_Applicable` drives a visual cue on page 3 (only Delhi is `TRUE`) —
this is the same distinction the README's GRAP table makes.

## 4. Relationships (star schema)

**Modeling → Manage Relationships**, create (all single-direction,
many-to-one, from fact to dimension):

- `Fact_Daily[city]` → `Dim_City[City]`
- `Fact_Daily[date]` → `Dim_Date[Date]`
- `Fact_Rolling30[city]` → `Dim_City[City]`
- `Fact_Rolling30[date]` → `Dim_Date[Date]`
- `Fact_MonthlyProfile[city]` → `Dim_City[City]`
- `Fact_Exceedance[city]` → `Dim_City[City]`
- `Fact_GRAP[city]` → `Dim_City[City]`
- `Fact_ANOVA[city]` → `Dim_City[City]`

Result: `Dim_City` and `Dim_Date` sit in the middle, every fact table
hangs off them — a real star schema, not a snowflake or a single flat
table.

## 5. DAX measures

Create these in a new empty table named `_Measures` (Modeling → New
Table → `_Measures = {}` isn't needed; just create the measures and set
their home table via the Model view, or create them directly on
`Fact_Daily`):

```
Avg PM2.5 = AVERAGE(Fact_Daily[avg_value])

Avg Rolling 30d PM2.5 = AVERAGE(Fact_Rolling30[rolling_30d_avg])

Exceedance % = AVERAGE(Fact_Exceedance[pct_exceedance_days])

Selected City GRAP Status =
IF(
    SELECTEDVALUE(Dim_City[GRAP_Applicable]) = TRUE,
    "Under GRAP",
    "Not under GRAP"
)
```

`Fact_Daily` and `Fact_Rolling30` contain all 12 pollutants — add a
**Pollutant slicer** bound to `Fact_Daily[pollutant]` on pages 1 and 2 so
`Avg PM2.5` etc. respond to whichever pollutant is selected (name the
measures generically, e.g. "Avg Pollutant Value", if you want the slicer
to genuinely change what they show rather than always meaning PM2.5).

## 6. Page 1 — City comparison overview

- **Slicer**: `Dim_City[City]` (multi-select, all 8 checked by default),
  `Fact_Daily[pollutant]` (single-select, default PM2.5).
- **Line chart**: X = `Dim_Date[Date]`, Y = `Avg Rolling 30d PM2.5`,
  Legend = `Dim_City[City]` — reproduces the rolling-average chart from
  the README, interactively.
- **Bar chart**: X = `Dim_City[City]`, Y = `Fact_Exceedance[pct_exceedance_days]`,
  sorted descending — reproduces the exceedance-day summary table.
- **Card**: `Avg PM2.5` for the current filter context.

## 7. Page 2 — Single-city drill-down

- **Slicer**: `Dim_City[City]`, single-select, one city at a time.
- **Line chart**: `Fact_Rolling30`, X = Date, Y = `rolling_30d_avg`,
  filtered to the slicer's city — the per-city rolling average panel.
- **Line/column chart**: `Fact_MonthlyProfile`, X = `calendar_month`
  (sort by the numeric column, not alphabetically), Y = `avg_value` —
  the seasonal profile for that one city.
- **Card**: `Exceedance %` for the selected city.

## 8. Page 3 — GRAP before/after

- **Clustered column chart**: `Fact_GRAP`, X = `city`, Y = `mean_pre` and
  `mean_post` as two series — reproduces the before/after bar chart from
  the README. Filter out rows where `status = "insufficient_data"`
  (Mumbai, Kolkata) or show them as a separate visual noting "not
  testable."
- **Table**: `Fact_GRAP` — city, n_pre, n_post, pct_change, p_value,
  cohens_d, significant_at_05.
- **Table or bar chart**: `Fact_ANOVA` — city, mean_pm25, sd_pm25 (the
  one-way ANOVA group means).
- **Text box**: paste the GRAP interpretation paragraph from the README
  ("every one of the 6 testable cities... a plain before/after comparison
  can't separate a GRAP effect from...") — a dashboard with a significant
  result and no caveat is exactly the naive read this project argues
  against.

## 9. Finish

- Save as `powerbi/air_quality_dashboard.pbix`.
- Export each page as PNG (File → Export → Export to PDF works too, but
  PNG per page is easier to embed): save to
  `reports/figures/powerbi_page1_overview.png`,
  `..._page2_drilldown.png`, `..._page3_grap.png`.
- Add the 3 screenshots + a short paragraph to the README's Power BI
  section, and commit the `.pbix` (it's small, no reason to gitignore it).
