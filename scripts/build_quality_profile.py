"""Build the pre-cleaning data-quality profile and write it to reports/.

Run: uv run python scripts/build_quality_profile.py
"""

from __future__ import annotations

from air_quality_analysis.config import REPORTS_DIR
from air_quality_analysis.io_utils import load_tidy
from air_quality_analysis.profile import (
    build_quality_profile,
    summarize_by_city,
    summarize_by_pollutant,
)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    tidy = load_tidy()
    profile = build_quality_profile(tidy)
    profile.to_csv(REPORTS_DIR / "quality_profile_full.csv", index=False)

    by_city = summarize_by_city(profile)
    by_city.to_csv(REPORTS_DIR / "quality_profile_by_city.csv", index=False)

    by_pollutant = summarize_by_pollutant(profile)
    by_pollutant.to_csv(REPORTS_DIR / "quality_profile_by_pollutant.csv", index=False)

    pm25 = profile[profile["pollutant"] == "PM2.5"].drop(columns=["pollutant"])
    pm25.to_csv(REPORTS_DIR / "quality_profile_pm25_by_city_year.csv", index=False)

    print("Rows in full profile:", len(profile))
    print("\n=== By city (all pollutants, all years) ===")
    print(by_city.to_string(index=False))
    print("\n=== By pollutant (all cities, all years) ===")
    print(by_pollutant.to_string(index=False))
    print("\n=== PM2.5 by city/year ===")
    print(pm25.to_string(index=False))


if __name__ == "__main__":
    main()
