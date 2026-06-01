"""TopCV crawler"""

import re
import time
from datetime import datetime
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup

from scraping.base_crawler import BaseCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default base URL and listing path for TopCV
BASE_URL = "https://www.topcv.vn"
LISTING_PATH = "/tim-viec-lam-cong-nghe-thong-tin-cr257"


class TopCVCrawler(BaseCrawler):
    """Crawler for TopCV (topcv.vn) IT job listings.

    Uses Selenium with a real browser to bypass Cloudflare.
    Tries Edge first (available on all Windows machines), then Chrome.

    Parameters
    ----------
    base_url : str
        Root URL of the TopCV site.
    delay : float
        Minimum seconds between requests to the same domain.
    max_retries : int
        Maximum retry attempts for transient network errors.
    headless : bool
        Run browser in headless mode (no visible window).
        Set to False if Cloudflare still blocks headless mode.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        delay: float = 3.0,
        max_retries: int = 5,
        headless: bool = True,
    ):
        super().__init__(source_name="topcv", delay=delay, max_retries=max_retries)
        self.base_url = base_url.rstrip("/")
        self.headless = headless
        self._driver = None

    # ------------------------------------------------------------------
    # Browser management
    # ------------------------------------------------------------------

    def _init_driver(self):
        if self._driver is not None:
            return

        # Try nodriver
        try:
            import nodriver
            import asyncio

            async def _start_browser():
                browser = await nodriver.start(headless=self.headless)
                return browser

            # Store reference to event loop and browser
            self._use_nodriver = True
            self._loop = asyncio.new_event_loop()
            self._browser = self._loop.run_until_complete(_start_browser())
            self._driver = True 
            logger.info("nodriver browser initialized (headless=%s)", self.headless)
            return
        except Exception as exc:
            logger.warning("nodriver failed: %s — trying Selenium Edge", exc)
            self._use_nodriver = False

        # Fallback to Selenium Edge
        try:
            from selenium import webdriver
            from selenium.webdriver.edge.options import Options as EdgeOptions

            options = EdgeOptions()
            if self.headless:
                options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--window-size=1920,1080")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            self._driver = webdriver.Edge(options=options)
            self._driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
            )
            self._use_nodriver = False
            logger.info("Selenium Edge driver initialized (headless=%s)", self.headless)
        except Exception as exc:
            logger.error("All browser init methods failed: %s", exc)
            raise RuntimeError("Could not initialize any browser driver.") from exc

    def _quit_driver(self):
        """Safely close the browser."""
        if self._use_nodriver and hasattr(self, '_browser') and self._browser:
            try:
                import asyncio
                self._loop.run_until_complete(self._browser.stop())
                self._loop.close()
            except Exception:
                pass
            self._browser = None
        elif self._driver and not self._use_nodriver:
            try:
                self._driver.quit()
            except Exception:
                pass
        self._driver = None

    def _fetch(self, url: str, wait_for_js: bool = True) -> Optional[str]:
        """Fetch a URL using the browser."""
        self._wait_for_delay(url)

        if self._use_nodriver:
            return self._fetch_nodriver(url)
        else:
            return self._fetch_selenium(url)

    def _fetch_nodriver(self, url: str) -> Optional[str]:
        """Fetch using nodriver."""
        import asyncio

        async def _get_page(url):
            tab = await self._browser.get(url)
            # Wait for page to fully load
            await asyncio.sleep(5)
            # Get page source
            source = await tab.get_content()
            return source

        for attempt in range(1, self.max_retries + 1):
            try:
                page_source = self._loop.run_until_complete(_get_page(url))

                if not page_source:
                    continue

                if "Just a moment" in page_source or "Attention Required" in page_source:
                    logger.warning("Cloudflare challenge for %s — waiting", url)
                    import asyncio as aio
                    self._loop.run_until_complete(aio.sleep(10))
                    page_source = self._loop.run_until_complete(_get_page(url))

                return page_source

            except Exception as exc:
                logger.error("nodriver error (attempt %d/%d) for %s: %s",
                             attempt, self.max_retries, url, str(exc)[:200])
                if attempt < self.max_retries:
                    time.sleep(3)

        return None

    def _fetch_selenium(self, url: str) -> Optional[str]:
        """Fetch using Selenium with session recovery."""
        for attempt in range(1, self.max_retries + 1):
            try:
                # Check if driver is still alive
                try:
                    _ = self._driver.title
                except Exception:
                    logger.warning("Driver session dead — reinitializing")
                    self._quit_driver()
                    self._init_driver()
                    time.sleep(2)

                self._driver.get(url)
                time.sleep(4)

                page_source = self._driver.page_source
                if "Attention Required" in page_source or "Just a moment" in page_source:
                    logger.warning("Cloudflare challenge for %s — waiting", url)
                    time.sleep(12)
                    page_source = self._driver.page_source
                    if "Attention Required" in page_source or "Just a moment" in page_source:
                        if attempt < self.max_retries:
                            continue
                        return None

                # Wait for JS content
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.ui import WebDriverWait
                try:
                    WebDriverWait(self._driver, 10).until(
                        lambda d: (
                            d.find_elements(By.CSS_SELECTOR, "a[href*='/viec-lam/']")
                            or d.find_elements(By.CSS_SELECTOR, ".job-detail__info--title")
                        )
                    )
                except Exception:
                    pass

                return self._driver.page_source

            except Exception as exc:
                exc_msg = str(exc)
                if "invalid session id" in exc_msg or "session deleted" in exc_msg:
                    logger.warning("Session crashed — reinitializing")
                    self._quit_driver()
                    self._init_driver()
                    time.sleep(3)
                    continue
                else:
                    logger.error("Browser error (attempt %d/%d): %s",
                                 attempt, self.max_retries, exc_msg[:200])
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)

        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def crawl(self, max_pages: Optional[int] = None) -> List[dict]:
        """Crawl TopCV IT job listings.

        Parameters
        ----------
        max_pages : int | None
            Maximum number of listing pages to crawl. None means
            crawl until no more pages are found.

        Returns
        -------
        list[dict]
            List of Job_Record dictionaries with all 16 fields.
        """
        self._start_session()
        records: List[dict] = []

        try:
            self._init_driver()
        except RuntimeError as exc:
            logger.error("Cannot start browser: %s", exc)
            self._end_session()
            return records

        page = 1
        try:
            while max_pages is None or page <= max_pages:
                page_url = f"{self.base_url}{LISTING_PATH}?page={page}"
                logger.info("Crawling TopCV listing page %d: %s", page, page_url)

                html = self._fetch(page_url)
                if html is None:
                    logger.warning("Failed to fetch listing page %d — stopping", page)
                    break

                job_urls = self._parse_listing_page(html)
                if not job_urls:
                    logger.info("No job links found on page %d — finished", page)
                    break

                self._total_pages += 1
                logger.info("Page %d: found %d job links", page, len(job_urls))

                for job_url in job_urls:
                    record = self._crawl_detail_page(job_url)
                    if record is not None:
                        records.append(record)
                        self._total_records += 1

                page += 1
        finally:
            self._quit_driver()

        self._end_session()
        logger.info("TopCV crawl complete: %d records collected", len(records))
        return records

    # ------------------------------------------------------------------
    # Listing page parsing
    # ------------------------------------------------------------------

    def _parse_listing_page(self, html: str) -> List[str]:
        """Extract job detail URLs from a TopCV listing page.

        TopCV listing pages contain job cards with links matching the
        pattern: /viec-lam/{slug}/{id}.html

        Parameters
        ----------
        html : str
            Raw HTML of the listing page.

        Returns
        -------
        list[str]
            Absolute URLs to individual job detail pages.
        """
        soup = BeautifulSoup(html, "html.parser")
        urls: List[str] = []
        seen: set = set()

        # /viec-lam/{slug}/{numeric_id}.html
        job_url_pattern = re.compile(r"/viec-lam/[^/]+/\d+\.html")

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if job_url_pattern.search(href):
                # Remove tracking query params for deduplication
                clean_url = href.split("?")[0]
                absolute_url = clean_url if clean_url.startswith("http") else f"{self.base_url}{clean_url}"
                if absolute_url not in seen:
                    seen.add(absolute_url)
                    urls.append(absolute_url)

        return urls

    # ------------------------------------------------------------------
    # Detail page crawling and parsing
    # ------------------------------------------------------------------

    def _crawl_detail_page(self, url: str) -> Optional[dict]:
        """Fetch and parse a single TopCV job detail page."""
        time.sleep(3)

        html = self._fetch(url)
        if html is None:
            return None

        try:
            return self._parse_detail_page(html, url)
        except Exception as exc:
            logger.error("Error parsing TopCV detail page %s: %s", url, exc)
            return None

    def _parse_detail_page(self, html: str, url: str) -> dict:
        """Parse a TopCV job detail page into a Job_Record dict."""
        soup = BeautifulSoup(html, "html.parser")

        # --- Job Title ---
        job_title = self._text(soup, ".job-detail__info--title")
        if not job_title:
            job_title = self._text(soup, "h1")

        # --- Company Name ---
        company_name = None
        company_el = soup.select_one(".company-name-label a")
        if not company_el:
            company_el = soup.select_one(".company-name-label")
        if company_el:
            company_name = company_el.get_text(strip=True)

        # --- Info sections (Salary, Location, Experience) ---
        info_values = soup.select(".job-detail__info--section-content-value")
        salary_text = info_values[0].get_text(strip=True) if len(info_values) > 0 else ""
        location = info_values[1].get_text(strip=True) if len(info_values) > 1 else ""
        experience_text = info_values[2].get_text(strip=True) if len(info_values) > 2 else ""

        salary_min, salary_max, salary_currency = self._parse_salary(salary_text)
        experience_required = self._parse_experience(experience_text)

        # --- Company Size & Field ---
        company_size = None
        company_values = soup.select(".company-value")
        if len(company_values) > 0:
            company_size = company_values[0].get_text(strip=True)

        # --- General Info (Level, Job Type) ---
        job_level = None
        job_type = None
        general_labels = soup.select(".box-general-group-info-title")
        general_values = soup.select(".box-general-group-info-value")
        for i, label_el in enumerate(general_labels):
            label_text = label_el.get_text(strip=True).lower()
            value = general_values[i].get_text(strip=True) if i < len(general_values) else ""
            if "cấp bậc" in label_text:
                job_level = value
            elif "hình thức" in label_text:
                job_type = value

        # --- Deadline ---
        deadline = None
        deadline_el = soup.select_one(".job-detail__info--deadline")
        if deadline_el:
            deadline_text = deadline_el.get_text(strip=True)
            date_match = re.search(r"\d{2}/\d{2}/\d{4}", deadline_text)
            if date_match:
                deadline = self._parse_date(date_match.group())

        # --- Skills ---
        skills = self._extract_skills(soup)

        # --- Job Description & Benefits ---
        jd_text = ""
        benefits_text = ""

        jd_sections = soup.select(".job-detail__information-detail--content")
        if jd_sections:
            full_content = jd_sections[0]
            current_section = ""
            current_text = []

            for child in full_content.children:
                if hasattr(child, 'name') and child.name == 'h3':
                    if current_section and current_text:
                        text_block = "\n".join(current_text)
                        if "mô tả" in current_section.lower():
                            jd_text = text_block
                        elif "quyền lợi" in current_section.lower():
                            benefits_text = text_block
                    current_section = child.get_text(strip=True)
                    current_text = []
                elif hasattr(child, 'get_text'):
                    t = child.get_text(strip=True)
                    if t:
                        current_text.append(t)

            # Save last section
            if current_section and current_text:
                text_block = "\n".join(current_text)
                if "mô tả" in current_section.lower():
                    jd_text = text_block
                elif "quyền lợi" in current_section.lower():
                    benefits_text = text_block

        # Fallback
        if not jd_text:
            desc_block = soup.select_one(".job-detail__information-detail")
            if desc_block:
                jd_text = desc_block.get_text(separator="\n", strip=True)

        # --- Posted date ---
        posted_date = datetime.now().strftime("%Y-%m-%d")

        return {
            "job_title": job_title or "",
            "company_name": company_name or "",
            "company_size": company_size or "",
            "location": location or "",
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "experience_required": experience_required,
            "skills": skills,
            "job_type": job_type or "",
            "job_level": job_level or "",
            "posted_date": posted_date,
            "deadline": deadline,
            "job_description": jd_text or "",
            "benefits": benefits_text or "",
            "source": "topcv",
        }

    # ------------------------------------------------------------------
    # Parsing utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _text(soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Return stripped text of the first element matching selector."""
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    @staticmethod
    def _parse_salary(text: Optional[str]) -> Tuple[Optional[float], Optional[float], str]:
        """Extract (salary_min, salary_max, currency) from salary string."""
        if not text:
            return None, None, "VND"

        text_lower = text.lower()
        if "thỏa thuận" in text_lower or "thoả thuận" in text_lower:
            return None, None, "VND"

        currency = "USD" if ("usd" in text_lower or "$" in text) else "VND"

        cleaned = text.replace(",", "").replace(".", "")
        numbers = re.findall(r"\d+", cleaned)

        if not numbers:
            return None, None, currency

        nums = [float(n) for n in numbers]

        if len(nums) >= 2:
            return min(nums), max(nums), currency

        val = nums[0]
        if "tới" in text_lower or "đến" in text_lower:
            return None, val, currency
        elif "từ" in text_lower:
            return val, None, currency
        else:
            return val, val, currency

    @staticmethod
    def _parse_experience(text: Optional[str]) -> Optional[float]:
        """Extract numeric years of experience from text."""
        if not text:
            return None
        text_lower = text.lower()
        if "không" in text_lower or "chưa" in text_lower:
            return 0.0
        match = re.search(r"(\d+)", text)
        return float(match.group(1)) if match else None

    @staticmethod
    def _parse_date(text: Optional[str]) -> Optional[str]:
        """Parse a date string into ISO format (YYYY-MM-DD)."""
        if not text:
            return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return text

    @staticmethod
    def _extract_skills(soup: BeautifulSoup) -> List[str]:
        """Extract skill names from tag elements on the detail page."""
        skills: List[str] = []

        # Primary: box-category tags (confirmed working)
        for tag in soup.select(".box-category-tag"):
            skill = tag.get_text(strip=True)
            if skill:
                skills.append(skill)

        if not skills:
            for tag in soup.select(".job-detail__tag-item"):
                skill = tag.get_text(strip=True)
                if skill:
                    skills.append(skill)

        if not skills:
            for tag in soup.select(".tag-item"):
                skill = tag.get_text(strip=True)
                if skill:
                    skills.append(skill)

        return skills
