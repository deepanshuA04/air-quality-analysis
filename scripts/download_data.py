"""Download the raw CPCB air-quality CSVs from Kaggle into data/raw/.

Source: "Air Quality Data in India (2015 - 2020)" by rohanrao, CC0-1.0.
https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india

Requires Kaggle API credentials to be configured (kaggle.json, KAGGLE_USERNAME/
KAGGLE_KEY env vars, or the newer KAGGLE_API_TOKEN / ~/.kaggle/access_token) —
see https://www.kaggle.com/docs/api. Run with: uv run python scripts/download_data.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

DATASET = "rohanrao/air-quality-data-in-india"
FILES = ["city_hour.csv", "city_day.csv", "stations.csv"]
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
CHECKSUM_FILE = RAW_DIR / "CHECKSUMS.sha256"


def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "kaggle",
                "datasets",
                "download",
                DATASET,
                "-f",
                name,
                "-p",
                str(RAW_DIR),
                "--force",
            ],
            check=True,
        )
        zip_path = RAW_DIR / f"{name}.zip"
        if zip_path.exists():
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(RAW_DIR)
            zip_path.unlink()


def write_checksums() -> None:
    lines = []
    for name in sorted(FILES):
        path = RAW_DIR / name
        if path.exists():
            lines.append(f"{sha256sum(path)}  {name}")
    CHECKSUM_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_checksums() -> bool:
    if not CHECKSUM_FILE.exists():
        return False
    ok = True
    for line in CHECKSUM_FILE.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        path = RAW_DIR / name
        if not path.exists() or sha256sum(path) != digest:
            print(f"CHECKSUM MISMATCH: {name}")
            ok = False
    return ok


if __name__ == "__main__":
    download()
    write_checksums()
    print(f"Wrote checksums to {CHECKSUM_FILE}")
