"""Chạy crawlers → data/raw/{source}_{date}.csv

Usage:
    python scripts/run_crawlers.py --all --max-pages 5
    python scripts/run_crawlers.py --source topcv --max-pages 3
    python scripts/run_crawlers.py --source linkedin --max-pages 10
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.logger import get_logger

logger = get_logger("run_crawlers")

def run_topcv(max_pages=None):
    from scraping.topcv_crawler import TopCVCrawler
    logger.info("=== Crawling TopCV ===")
    crawler = TopCVCrawler()
    records = crawler.crawl(max_pages=max_pages)
    crawler.save_raw(records)
    report = crawler.generate_report()
    logger.info("TopCV: %d records, %d errors, %.1fs", report.total_records, report.total_errors, report.duration_seconds)
    return len(records)

def run_itviec(max_pages=None):
    from scraping.itviec_crawler import ITviecCrawler
    logger.info("=== Crawling ITviec ===")
    crawler = ITviecCrawler()
    records = crawler.crawl(max_pages=max_pages)
    crawler.save_raw(records)
    report = crawler.generate_report()
    logger.info("ITviec: %d records, %d errors, %.1fs",report.total_records, report.total_errors, report.duration_seconds)
    return len(records)


def run_linkedin(max_pages=None):
    from scraping.linkedin_crawler import LinkedInCrawler
    logger.info("=== Crawling LinkedIn ===")
    crawler = LinkedInCrawler(keywords="IT", geo_id="104195383", location="Vietnam")
    records = crawler.crawl(max_pages=max_pages)
    crawler.save_raw(records)
    report = crawler.generate_report()
    logger.info("LinkedIn: %d records, %d errors, %.1fs",report.total_records, report.total_errors, report.duration_seconds)
    return len(records)


def run_careerviet(max_pages=None):
    from scraping.careerviet_crawler import CareerVietCrawler
    logger.info("=== Crawling CareerViet ===")
    crawler = CareerVietCrawler()
    records = crawler.crawl(max_pages=max_pages)
    crawler.save_raw(records)
    report = crawler.generate_report()
    logger.info("CareerViet: %d records, %d errors, %.1fs",report.total_records, report.total_errors, report.duration_seconds)
    return len(records)

CRAWLERS = {
    "topcv": run_topcv,
    "itviec": run_itviec,
    "linkedin": run_linkedin,
    "careerviet": run_careerviet,
}

def main():
    parser = argparse.ArgumentParser(description="Crawl job data -> data/raw/")
    parser.add_argument("--source", choices=list(CRAWLERS.keys()))
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--max-pages", type=int, default=None)
    args = parser.parse_args()

    if not args.source and not args.all:
        parser.print_help()
        sys.exit(1)

    total = 0
    if args.source:
        total += CRAWLERS[args.source](max_pages=args.max_pages)
    elif args.all:
        for name, fn in CRAWLERS.items():
            try:
                total += fn(max_pages=args.max_pages)
            except Exception as exc:
                logger.error("Crawler '%s' failed: %s", name, exc)
    
    logger.info("TOTAL: %d records saved to data/raw/", total)

if __name__ == "__main__":
    main()