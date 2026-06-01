"""Feature Engineering: cleaned → data/features/jobs_featured_full.csv

Usage:
    python scripts/run_features.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.config import DATA_PROCESSED
from src.features.feature_engineer import FeatureEngineer
from src.utils.logger import get_logger

logger = get_logger("run_features")

INPUT = DATA_PROCESSED / "jobs_cleaned_full.csv"


def main():
    logger.info("=" * 50)
    logger.info("FEATURE ENGINEERING PIPELINE")
    logger.info("=" * 50)

    if not INPUT.exists():
        logger.error("Input file not found: %s", INPUT)
        logger.error("Run scripts/run_etl.py first.")
        sys.exit(1)

    df = pd.read_csv(INPUT, encoding="utf-8")
    logger.info("Loaded %d records, %d columns", len(df), len(df.columns))

    fe = FeatureEngineer()
    df_featured = fe.engineer_features(df)

    logger.info("=" * 50)
    logger.info("SUMMARY")
    logger.info("  Records: %d", len(df_featured))
    logger.info("  Columns: %d", len(df_featured.columns))
    logger.info("  Salary available: %d", df_featured["salary_avg"].notna().sum())
    logger.info("=" * 50)


if __name__ == "__main__":
    main()