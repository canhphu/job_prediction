"""Abstract base class for all web crawlers.

Provides shared infrastructure for responsible web crawling:
- robots.txt compliance checking
- Minimum delay between requests to the same domain
- Retry logic with exponential backoff for network errors
- Raw data persistence to CSV
- Crawl session reporting via CrawlReport
"""

import csv
import os
import time
import urllib.robotparser
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

from src.config import CRAWL_DELAY, DATA_RAW, MAX_RETRIES
from src.utils.data_reports import CrawlError, CrawlReport
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseCrawler(ABC):
    """Abstract base class cho tất cả crawler.

    Parameters
    ----------
    source_name : str
        Identifier for the data source (e.g. "topcv", "itviec").
    delay : float
        Minimum seconds between consecutive requests to the same domain.
        Defaults to ``CRAWL_DELAY`` from config (2.0 s).
    max_retries : int
        Maximum retry attempts for transient network errors.
        Defaults to ``MAX_RETRIES`` from config (3).
    """

    def __init__(
        self,
        source_name: str,
        delay: float = CRAWL_DELAY,
        max_retries: int = MAX_RETRIES,
    ):
        self.source_name = source_name
        self.delay = max(delay, 2.0)  # enforce minimum 2-second delay
        self.max_retries = max_retries

        # Per-domain timestamps for rate-limiting
        self._last_request_time: Dict[str, float] = {}

        # Session-level tracking
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._total_pages: int = 0
        self._total_records: int = 0
        self._errors: List[CrawlError] = []

        # Cache parsed robots.txt per domain
        self._robots_cache: Dict[str, urllib.robotparser.RobotFileParser] = {}

    # ------------------------------------------------------------------
    # Abstract method — subclasses must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def crawl(self, max_pages: Optional[int] = None) -> List[dict]:
        """Thu thập Job_Record từ nguồn. Trả về list of dict."""
        ...

    # ------------------------------------------------------------------
    # robots.txt compliance
    # ------------------------------------------------------------------

    def check_robots_txt(self, base_url: str) -> bool:
        """Check whether crawling *base_url* is allowed by robots.txt.

        Uses ``urllib.robotparser`` to fetch and parse the robots.txt
        file for the given URL's domain.  Results are cached per domain
        so repeated checks are cheap.

        Parameters
        ----------
        base_url : str
            The URL to check.

        Returns
        -------
        bool
            ``True`` if crawling is allowed (or robots.txt cannot be
            fetched), ``False`` if explicitly disallowed.
        """
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{domain}/robots.txt"

        if domain not in self._robots_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
            except Exception as exc:
                logger.warning(
                    "Could not fetch robots.txt from %s: %s — allowing crawl",
                    robots_url,
                    exc,
                )
                return True
            self._robots_cache[domain] = rp

        rp = self._robots_cache[domain]
        allowed = rp.can_fetch("*", base_url)
        if not allowed:
            logger.warning(
                "robots.txt disallows crawling %s — skipping", base_url
            )
        return allowed

    # ------------------------------------------------------------------
    # Rate-limiting / delay
    # ------------------------------------------------------------------

    def _wait_for_delay(self, url: str) -> None:
        """Block until at least ``self.delay`` seconds have elapsed since
        the last request to the same domain.
        """
        domain = urlparse(url).netloc
        last = self._last_request_time.get(domain)
        if last is not None:
            elapsed = time.monotonic() - last
            remaining = self.delay - elapsed
            if remaining > 0:
                logger.debug("Sleeping %.2f s before next request to %s", remaining, domain)
                time.sleep(remaining)
        self._last_request_time[domain] = time.monotonic()

    # ------------------------------------------------------------------
    # Retry with exponential backoff
    # ------------------------------------------------------------------

    def fetch_with_retry(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Perform an HTTP GET with retry + exponential backoff.

        Retries up to ``self.max_retries`` times on network-level errors
        (``requests.RequestException``).  The backoff sequence is
        2 s → 4 s → 8 s (i.e. ``2 ** attempt`` seconds).

        HTTP-level errors (4xx / 5xx) are **not** retried — they are
        logged and ``None`` is returned immediately.

        Parameters
        ----------
        url : str
            Target URL.
        **kwargs
            Extra keyword arguments forwarded to ``requests.get``.

        Returns
        -------
        requests.Response | None
            The response object on success, or ``None`` when all retries
            are exhausted or an HTTP error is encountered.
        """
        self._wait_for_delay(url)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = requests.get(url, timeout=30, **kwargs)

                # HTTP errors — log and give up (no retry)
                if response.status_code >= 400:
                    error = CrawlError(
                        url=url,
                        error_code=response.status_code,
                        timestamp=datetime.now(),
                        message=f"HTTP {response.status_code}",
                    )
                    self._errors.append(error)
                    logger.error(
                        "HTTP error %d for %s at %s",
                        response.status_code,
                        url,
                        error.timestamp.isoformat(),
                    )
                    return None

                return response

            except requests.RequestException as exc:
                backoff = 2 ** attempt  # 2, 4, 8
                error = CrawlError(
                    url=url,
                    error_code=0,
                    timestamp=datetime.now(),
                    message=str(exc),
                )
                self._errors.append(error)
                logger.error(
                    "Network error (attempt %d/%d) for %s at %s: %s",
                    attempt,
                    self.max_retries,
                    url,
                    error.timestamp.isoformat(),
                    exc,
                )

                if attempt < self.max_retries:
                    logger.info("Retrying in %d s …", backoff)
                    time.sleep(backoff)
                else:
                    logger.error(
                        "All %d retries exhausted for %s — skipping",
                        self.max_retries,
                        url,
                    )

        return None

    # ------------------------------------------------------------------
    # Persist raw data
    # ------------------------------------------------------------------

    def save_raw(
        self,
        records: List[dict],
        output_dir: str = str(DATA_RAW),
    ) -> str:
        """Save crawled records as a CSV file.

        File naming convention: ``{source}_{YYYY-MM-DD}.csv``

        Parameters
        ----------
        records : list[dict]
            List of Job_Record dictionaries to persist.
        output_dir : str
            Directory to write the CSV into.  Defaults to ``data/raw/``.

        Returns
        -------
        str
            Absolute path of the written CSV file.
        """
        os.makedirs(output_dir, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{self.source_name}_{date_str}.csv"
        filepath = os.path.join(output_dir, filename)

        if not records:
            logger.warning("No records to save for source '%s'", self.source_name)
            # Write an empty CSV with headers from JobRecord fields
            fieldnames = [
                "job_title", "company_name", "company_size", "location",
                "salary_min", "salary_max", "salary_currency",
                "experience_required", "skills", "job_type", "job_level",
                "posted_date", "deadline", "job_description", "benefits",
                "source",
            ]
            with open(filepath, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=fieldnames)
                writer.writeheader()
            return filepath

        fieldnames = list(records[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        logger.info(
            "Saved %d records to %s",
            len(records),
            filepath,
        )
        return filepath

    # ------------------------------------------------------------------
    # Crawl report
    # ------------------------------------------------------------------

    def generate_report(self) -> CrawlReport:
        """Create a summary report for the completed crawl session.

        Returns
        -------
        CrawlReport
            Dataclass containing total pages, records, errors, and
            timing information.
        """
        end = self._end_time or datetime.now()
        start = self._start_time or end
        duration = (end - start).total_seconds()

        report = CrawlReport(
            source=self.source_name,
            total_pages=self._total_pages,
            total_records=self._total_records,
            total_errors=len(self._errors),
            duration_seconds=duration,
            start_time=start,
            end_time=end,
            errors=list(self._errors),
        )

        logger.info(
            "Crawl report for '%s': pages=%d, records=%d, errors=%d, duration=%.1f s",
            report.source,
            report.total_pages,
            report.total_records,
            report.total_errors,
            report.duration_seconds,
        )
        return report

    # ------------------------------------------------------------------
    # Session helpers (for use by subclasses)
    # ------------------------------------------------------------------

    def _start_session(self) -> None:
        """Mark the beginning of a crawl session."""
        self._start_time = datetime.now()
        self._total_pages = 0
        self._total_records = 0
        self._errors = []
        logger.info("Crawl session started for '%s' at %s", self.source_name, self._start_time.isoformat())

    def _end_session(self) -> None:
        """Mark the end of a crawl session."""
        self._end_time = datetime.now()
        logger.info("Crawl session ended for '%s' at %s", self.source_name, self._end_time.isoformat())
