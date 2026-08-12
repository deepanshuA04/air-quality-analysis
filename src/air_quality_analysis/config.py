"""Shared constants: cities, pollutants, plausibility ceilings, file paths."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
SQL_DIR = ROOT / "sql"
DB_PATH = PROCESSED_DIR / "air_quality.sqlite"

CITY_HOUR_CSV = RAW_DIR / "city_hour.csv"

# The 8 cities with the longest, most complete hourly coverage in the raw
# file (see README "Coverage vs. the original plan"). Chosen over the full
# 26-city set for geographic spread (N/S/E/W India) and enough pre/post
# history for the intervention analysis in milestone 6.
CITIES = [
    "Delhi",
    "Mumbai",
    "Kolkata",
    "Chennai",
    "Bengaluru",
    "Hyderabad",
    "Ahmedabad",
    "Lucknow",
]

POLLUTANTS = [
    "PM2.5",
    "PM10",
    "NO",
    "NO2",
    "NOx",
    "NH3",
    "CO",
    "SO2",
    "O3",
    "Benzene",
    "Toluene",
    "Xylene",
]

# Units as reported by CPCB / the source dataset: µg/m3 for everything
# except CO, which is mg/m3.
POLLUTANT_UNITS = {p: ("mg/m3" if p == "CO" else "ug/m3") for p in POLLUTANTS}

# Physically-plausible ambient ceilings, used to flag impossible values
# (see cleaning.flag_impossible_values). Chosen generously so that real
# severe-pollution events (e.g. Delhi winter smog) are NOT flagged — these
# only catch instrument faults / unit errors, not organic extremes.
PLAUSIBLE_CEILING = {
    "PM2.5": 1000.0,   # documented ambient extremes in Delhi winter smog approach ~1000 ug/m3
    "PM10": 1000.0,    # same order as PM2.5 during combined smog+dust events
    "NO": 500.0,       # roadside NOx rarely sustains hundreds of ug/m3; >500 is an outlier reading
    "NO2": 500.0,
    "NOx": 500.0,
    "NH3": 500.0,
    "CO": 50.0,        # CPCB 24h standard is 2 mg/m3; >50 mg/m3 ambient is not physically credible
    "SO2": 200.0,       # far above the CPCB 24h standard of 80 ug/m3
    "O3": 500.0,
    "Benzene": 500.0,
    "Toluene": 500.0,
    "Xylene": 500.0,
}

# Pollutants for which an exact-zero reading is treated as "sensor off"
# rather than a genuine measurement: true ambient particulate matter is
# never exactly zero. Gaseous pollutants (CO, Benzene, Toluene, Xylene,
# NOx) legitimately read 0 near their detection limit, so they are
# deliberately excluded from this rule.
ZERO_IS_IMPOSSIBLE = {"PM2.5", "PM10"}

# CPCB National Ambient Air Quality Standard for PM2.5, 24-hour average,
# ug/m3 (used for exceedance-day counting in the SQL views).
CPCB_PM25_24H_STANDARD = 60.0

# Gap-length thresholds for the cleaning pipeline (in hours).
SHORT_GAP_MAX_HOURS = 6
