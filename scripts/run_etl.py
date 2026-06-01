"""ETL: raw files → interim (cleaned riêng lẻ) → append vào processed/jobs_cleaned_full.csv

Usage:
    python scripts/run_etl.py
    python scripts/run_etl.py --reprocess-all   # Xử lý lại toàn bộ
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

def load_processed_logs() -> list:
    if PROCESSED_LOG.exists():
        with open(PROCESSED_LOG, "r") as f:
            data = json.load(f)
        return data.get("processed", [])
    return []

def save_processed_logs(files: list):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_LOG, "w") as f:
        json.dump({"processed": files}, f, indent=2)

def get_raw_files(reprocess_all: bool = False) -> list:
    all_files = sorted(DATA_RAW.glob("*.csv"))
    if reprocess_all:
        return all_files
    processed = set(load_processed_log())
    return [f for f in all_files if f.name not in processed]

def main():
    parser = argparse.ArgumentParser(description="ETL: raw -> interim -> cleaned")
    parser.add_argument("--reprocess-all", action="store_true", help="Reprocess all raw files from scratch")
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

            # Save to interim: nguồn_ngày_cleaned.csv
            interim_name = fpath.stem + "_cleaned.csv"
            interim_path = DATA_INTERIM / interim_name
            df_cleaned.to_csv(interim_path, index=False, encoding="utf-8")
            logger.info("  Saved interim: %s", interim_name)
            interim_files.append(interim_path)

        except Exception as exc:
            logger.error("  Failed to process %s: %s", fpath.name, exc)

    if not interim_files:
        logger.warning("No files were successfully cleaned.")
        return

    # Step 2: Append all new interim files to jobs_cleaned_full.csv
    frames = []
    for ipath in interim_files:
        frames.append(pd.read_csv(ipath, dtype=str))

    df_new = pd.concat(frames, ignore_index=True)
    logger.info("Total new cleaned records: %d", len(df_new))

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    if OUTPUT_FILE.exists() and not args.reprocess_all:
        df_existing = pd.read_csv(OUTPUT_FILE, dtype=str)
        logger.info("Existing cleaned file: %d records", len(df_existing))
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        # Dedup on full dataset
        before = len(df_combined)
        df_combined = df_combined.drop_duplicates(
            subset=["job_title", "company_name", "source"], keep="first"
        ).reset_index(drop=True)
        logger.info("Combined + dedup: %d → %d", before, len(df_combined))
    else:
        df_combined = df_new

    # Save
    df_combined.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
    logger.info("Saved: %s (%d records)", OUTPUT_FILE, len(df_combined))

    # Update processed log
    processed = load_processed_log() if not args.reprocess_all else []
    for f in new_files:
        if f.name not in processed:
            processed.append(f.name)
    save_processed_log(processed)

    logger.info("=" * 50)
    logger.info("ETL COMPLETE")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()