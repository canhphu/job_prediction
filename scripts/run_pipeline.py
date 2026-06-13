"""Pipeline: crawl → etl → features.

Usage:
    python scripts/run_pipeline.py --all --max-pages 5
    python scripts/run_pipeline.py --source topcv --max-pages 3
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.logger import get_logger

logger = get_logger("run_pipeline")


def run_step(script: str, args: list = None):
    """Run a script as subprocess."""
    cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / script)]
    if args:
        cmd.extend(args)
    logger.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        logger.error("Script %s failed with code %d", script, result.returncode)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Full pipeline: crawl → etl → features")
    parser.add_argument("--source", choices=["topcv", "itviec", "linkedin", "careerviet"])
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--skip-crawl", action="store_true", help="Skip crawling, only run ETL + features")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("FULL PIPELINE START")
    logger.info("=" * 60)

    # Step 1: Crawl
    if not args.skip_crawl:
        crawl_args = []
        if args.source:
            crawl_args.extend(["--source", args.source])
        elif args.all:
            crawl_args.append("--all")
        else:
            logger.error("Specify --source or --all (or --skip-crawl)")
            sys.exit(1)
        if args.max_pages:
            crawl_args.extend(["--max-pages", str(args.max_pages)])

        if not run_step("run_crawlers.py", crawl_args):
            logger.error("Crawling failed. Stopping.")
            sys.exit(1)

    # Step 2: ETL
    if not run_step("run_etl.py"):
        logger.error("ETL failed. Stopping.")
        sys.exit(1)

    # Step 3: Feature Engineering
    if not run_step("run_features.py"):
        logger.error("Feature engineering failed. Stopping.")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("FULL PIPELINE COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()