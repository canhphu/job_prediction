"""ETL: raw files → interim (cleaned riêng lẻ) → append vào processed/jobs_cleaned_full.csv

Luồng:
1. Tìm file raw mới chưa xử lý
2. Clean từng file → lưu vào data/interim/{nguồn}_{ngày}_cleaned.csv
3. (Optional) Filter theo posted_date nếu có --date-from/--date-to
4. APPEND vào data/processed/jobs_cleaned_full.csv (giữ nguyên data cũ)
5. Dedup toàn bộ file combined
6. Cập nhật logs/processed_files.json

Usage:
    python scripts/run_etl.py
    python scripts/run_etl.py --date-from 2026-05-29 --date-to 2026-06-02
    python scripts/run_etl.py --reprocess-all
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.config import DATA_INTERIM, DATA_PROCESSED, DATA_RAW, LOGS_DIR
from src.etl.cleaner import Cleaner
from src.utils.logger import get_logger

logger = get_logger("run_etl")

PROCESSED_LOG = LOGS_DIR / "processed_files.json"
OUTPUT_FILE = DATA_PROCESSED / "jobs_cleaned_full.csv"


def load_processed_log() -> list:
    if PROCESSED_LOG.exists():
        with open(PROCESSED_LOG, "r") as f:
            data = json.load(f)
        return data.get("processed", [])
    return []


def save_processed_log(files: list):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_LOG, "w") as f:
        json.dump({"processed": files}, f, indent=2)


def get_new_raw_files(reprocess_all: bool = False) -> list:
    """Find raw CSV files that haven't been processed yet."""
    all_files = sorted(DATA_RAW.glob("*.csv"))
    if reprocess_all:
        return all_files
    processed = set(load_processed_log())
    return [f for f in all_files if f.name not in processed]


def filter_by_date(df: pd.DataFrame, date_from: str = None, date_to: str = None) -> pd.DataFrame:
    """Filter records by posted_date range. Only applied to NEW data before appending."""
    if not date_from and not date_to:
        return df
    if "posted_date" not in df.columns:
        return df

    # Only filter rows that have a valid posted_date
    has_date = df["posted_date"].notna() & (df["posted_date"].str.len() >= 10)

    mask = pd.Series([True] * len(df), index=df.index)
    if date_from:
        mask = mask & (~has_date | (df["posted_date"] >= date_from))
    if date_to:
        mask = mask & (~has_date | (df["posted_date"] <= date_to))

    before = len(df)
    df = df[mask].reset_index(drop=True)
    logger.info("Date filter (%s to %s): %d → %d records",
                date_from or "start", date_to or "end", before, len(df))
    return df


def main():
    parser = argparse.ArgumentParser(description="ETL: raw → interim → cleaned")
    parser.add_argument("--reprocess-all", action="store_true",
                        help="Reprocess all raw files (rebuild interim, but still APPEND to existing processed)")
    parser.add_argument("--date-from", type=str, default=None,
                        help="Only keep new records posted on or after this date (YYYY-MM-DD)")
    parser.add_argument("--date-to", type=str, default=None,
                        help="Only keep new records posted on or before this date (YYYY-MM-DD)")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("ETL PIPELINE START")
    logger.info("=" * 50)

    new_files = get_new_raw_files(reprocess_all=args.reprocess_all)
    if not new_files:
        logger.info("No new raw files to process.")
        return

    logger.info("Found %d new raw file(s) to process:", len(new_files))
    for f in new_files:
        logger.info("  - %s", f.name)

    cleaner = Cleaner()
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    interim_files = []

    # Step 1: Clean each raw file → save to interim
    for fpath in new_files:
        try:
            df = pd.read_csv(fpath, dtype=str)
            logger.info("  Loaded %s: %d rows", fpath.name, len(df))

            df_cleaned = cleaner.clean(df)
            logger.info("  After cleaning: %d rows", len(df_cleaned))

            if len(df_cleaned) == 0:
                logger.info("  No records after cleaning — skipping")
                continue

            # Save to interim (full cleaned, no date filter)
            interim_name = fpath.stem + "_cleaned.csv"
            interim_path = DATA_INTERIM / interim_name
            df_cleaned.to_csv(interim_path, index=False, encoding="utf-8")
            logger.info("  Saved interim: %s (%d rows)", interim_name, len(df_cleaned))
            interim_files.append(interim_path)

        except Exception as exc:
            logger.error("  Failed to process %s: %s", fpath.name, exc)

    if not interim_files:
        logger.warning("No files were successfully cleaned.")
        return

    # Step 2: Concat all new interim files
    frames = []
    for ipath in interim_files:
        frames.append(pd.read_csv(ipath, dtype=str))

    df_new = pd.concat(frames, ignore_index=True)
    logger.info("Total new cleaned records: %d", len(df_new))

    # Step 3: Apply date filter to NEW data only (does NOT affect existing data)
    if args.date_from or args.date_to:
        df_new = filter_by_date(df_new, args.date_from, args.date_to)
        if len(df_new) == 0:
            logger.warning("No records remain after date filter.")
            return

    # Step 4: APPEND to existing jobs_cleaned_full.csv
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    if OUTPUT_FILE.exists():
        df_existing = pd.read_csv(OUTPUT_FILE, dtype=str)
        logger.info("Existing cleaned file: %d records", len(df_existing))
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        logger.info("No existing cleaned file — creating new")
        df_combined = df_new

    # Step 5: Dedup on full combined dataset
    before = len(df_combined)
    df_combined = df_combined.drop_duplicates(
        subset=["job_title", "company_name", "source"], keep="first"
    ).reset_index(drop=True)
    logger.info("Combined + dedup: %d → %d (removed %d dupes)",
                before, len(df_combined), before - len(df_combined))

    # Step 6: Sort by posted_date descending (newest first)
    if "posted_date" in df_combined.columns:
        df_combined = df_combined.sort_values(
            by="posted_date", ascending=False, na_position="last"
        ).reset_index(drop=True)
        logger.info("Sorted by posted_date descending")

    # Save
    df_combined.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    logger.info("Saved: %s (%d records)", OUTPUT_FILE, len(df_combined))

    # Update processed log
    processed = load_processed_log()
    for f in new_files:
        if f.name not in processed:
            processed.append(f.name)
    save_processed_log(processed)

    logger.info("=" * 50)
    logger.info("ETL COMPLETE")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
