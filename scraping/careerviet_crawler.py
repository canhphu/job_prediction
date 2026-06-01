"""CareerViet crawler"""

import re
from datetime import datetime
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from scraping.base_crawler import BaseCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Base URL and listing path for CareerViet IT jobs (CNTT - Phan mem)
BASE_URL = "https://careerviet.vn"
LISTING_PATH = "/viec-lam/tim-viec-lam-it-phan-mem-c1-trang-{page}-vi.html"


class CareerVietCrawler(BaseCrawler):
    """Crawler for CareerViet (careerviet.vn) IT job listings.

    Parameters
    ----------
    base_url : str
        Root URL of the CareerViet site.
    delay : float
        Minimum seconds between requests to the same domain.
    max_retries : int
        Maximum retry attempts for transient network errors.
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        delay: float = 2.0,
        max_retries: int = 3,
    ):
        super().__init__(source_name="careerviet", delay=delay, max_retries=max_retries)
        self.base_url = base_url.rstrip("/")
        self._robots_checked = False
        self._robots_allowed = True
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def check_robots_txt(self, url: str) -> bool:
        if self._robots_checked:
            return self._robots_allowed
        self._robots_checked = True
        self._robots_allowed = super().check_robots_txt(url)
        return self._robots_allowed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def crawl(self, max_pages: Optional[int] = None) -> List[dict]:
        """Crawl CareerViet IT job listings.

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

        # Check robots.txt
        listing_url = self.base_url + LISTING_PATH.format(page=1)
        if not self.check_robots_txt(listing_url):
            logger.warning("CareerViet robots.txt disallows crawling - aborting")
            self._end_session()
            return records

        page = 1
        while max_pages is None or page <= max_pages:
            page_url = self.base_url + LISTING_PATH.format(page=page)
            logger.info("Crawling CareerViet listing page %d: %s", page, page_url)

            response = self.fetch_with_retry(page_url, headers=self._headers)
            if response is None:
                logger.warning("Failed to fetch listing page %d - stopping", page)
                break

            jobs_on_page = self._parse_listing_page(response.text)
            if not jobs_on_page:
                logger.info("No job cards found on page %d - finished", page)
                break

            self._total_pages += 1
            logger.info("Page %d: found %d jobs", page, len(jobs_on_page))

            for idx, job_data in enumerate(jobs_on_page, 1):
                # Fetch detail page for additional info
                detail_url = job_data.pop("_detail_url", None)
                if detail_url:
                    detail_record = self._crawl_detail_page(detail_url)
                    if detail_record:
                        job_data = self._merge_records(job_data, detail_record)

                records.append(job_data)
                self._total_records += 1

                # Progress log every 10 jobs
                if idx % 10 == 0:
                    logger.info("  Page %d progress: %d/%d jobs done", page, idx, len(jobs_on_page))

            page += 1

        self._end_session()
        logger.info("CareerViet crawl complete: %d records collected", len(records))
        return records

    # ------------------------------------------------------------------
    # Listing page parsing
    # ------------------------------------------------------------------

    def _parse_listing_page(self, html: str) -> List[dict]:
        """Extract job records from a CareerViet listing page.

        Parameters
        ----------
        html : str
            Raw HTML of the listing page.

        Returns
        -------
        list[dict]
            List of Job_Record dicts with _detail_url for detail crawling.
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs: List[dict] = []

        # Each job card is inside a div.figcaption
        job_cards = soup.select("div.figcaption")

        for card in job_cards:
            job = self._parse_job_card(card)
            if job and job.get("job_title"):
                jobs.append(job)

        return jobs

    def _parse_job_card(self, card: Tag) -> Optional[dict]:
        """Parse a single job card (div.figcaption) into a Job_Record dict.

        Parameters
        ----------
        card : Tag
            BeautifulSoup Tag for div.figcaption.

        Returns
        -------
        dict | None
        """
        try:
            # --- Job title + URL ---
            title_link = card.select_one("div.title h2 a.job_link")
            if not title_link:
                # Fallback: any a.job_link inside a h2
                title_link = card.select_one("h2 a.job_link")
            if not title_link:
                return None

            job_title = title_link.get_text(strip=True)
            if not job_title:
                return None

            # Remove "(MỚI)" suffix
            job_title = re.sub(r"\s*\(MỚI\)\s*$", "", job_title)

            href = title_link.get("href", "")
            detail_url = href if href.startswith("http") else f"{self.base_url}{href}"

            # Job ID from data-id attribute
            job_id = title_link.get("data-id", "")

            # --- Company name ---
            company_name = ""
            company_el = card.select_one("a.company-name")
            if company_el:
                company_name = company_el.get_text(strip=True)

            # --- Salary ---
            salary_min = None
            salary_max = None
            salary_currency = "VND"
            salary_el = card.select_one("div.salary p")
            if salary_el:
                salary_text = salary_el.get_text(strip=True)
                # Remove "Lương:" or "Lương :" prefix
                salary_text = re.sub(r"^Lương\s*:\s*", "", salary_text)
                salary_min, salary_max, salary_currency = self._parse_salary(salary_text)

            # --- Location ---
            location = ""
            location_el = card.select_one("div.location")
            if location_el:
                loc_items = location_el.select("li")
                if loc_items:
                    location = ", ".join(li.get_text(strip=True) for li in loc_items)
                else:
                    location = location_el.get_text(strip=True)

            # --- Deadline and Posted date ---
            deadline = None
            posted_date = None
            time_els = card.select("div.time time")
            if len(time_els) >= 1:
                deadline = self._parse_date(time_els[0].get_text(strip=True))
            if len(time_els) >= 2:
                posted_date = self._parse_date(time_els[1].get_text(strip=True))

            # --- Benefits/welfare ---
            benefits = ""
            welfare_el = card.select("ul.welfare li")
            if welfare_el:
                benefits = "; ".join(li.get_text(strip=True) for li in welfare_el)

            return {
                "job_title": job_title,
                "company_name": company_name,
                "company_size": None,
                "location": location,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": salary_currency,
                "experience_required": None,
                "skills": [],
                "job_type": "",
                "job_level": "",
                "posted_date": posted_date,
                "deadline": deadline,
                "job_description": "",
                "benefits": benefits,
                "source": "careerviet",
                "_detail_url": detail_url,
            }
        except Exception as exc:
            logger.debug("Error parsing job card: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Detail page crawling and parsing
    # ------------------------------------------------------------------

    def _crawl_detail_page(self, url: str) -> Optional[dict]:
        """Fetch and parse a single CareerViet job detail page.

        Parameters
        ----------
        url : str
            URL of the job detail page.

        Returns
        -------
        dict | None
            Additional fields extracted from detail page.
        """
        if not self.check_robots_txt(url):
            return None

        logger.debug("Fetching detail: %s", url)
        response = self.fetch_with_retry(url, headers=self._headers)
        if response is None:
            logger.warning("Detail page failed: %s", url[:80])
            return None

        try:
            result = self._parse_detail_page(response.text, url)
            return result
        except Exception as exc:
            logger.error("Error parsing CareerViet detail page %s: %s", url, exc)
            return None

    def _parse_detail_page(self, html: str, url: str) -> dict:
        """Parse a CareerViet job detail page.

        Parameters
        ----------
        html : str
            Raw HTML of the detail page.
        url : str
            URL of the page (for logging).

        Returns
        -------
        dict
            Job record fields from detail page.
        """
        soup = BeautifulSoup(html, "html.parser")

        # --- Job Title ---
        job_title = ""
        title_el = soup.select_one("h1, h2.title")
        if title_el:
            job_title = title_el.get_text(strip=True)

        # --- Company Name ---
        company_name = ""
        company_el = soup.select_one("a.company-name, a[href*='/nha-tuyen-dung/']")
        if company_el:
            company_name = company_el.get_text(strip=True)

        # --- Use page text for metadata extraction ---
        page_text = soup.get_text(separator="\n", strip=True)

        # Experience
        experience_required = None
        exp_match = re.search(r"[Kk]inh nghiệm\s*\n?\s*(.+?)(?:\n|$)", page_text)
        if exp_match:
            experience_required = self._parse_experience(exp_match.group(1))

        # Job level
        job_level = ""
        level_match = re.search(r"[Cc]ấp bậc\s*\n?\s*(.+?)(?:\n|$)", page_text)
        if level_match:
            job_level = level_match.group(1).strip()

        # Job type
        job_type = ""
        type_match = re.search(r"[Hh]ình thức\s*\n?\s*(.+?)(?:\n|$)", page_text)
        if type_match:
            job_type = type_match.group(1).strip()

        # Company size
        company_size = ""
        size_match = re.search(r"[Qq]uy mô\s*\n?\s*(.+?)(?:\n|$)", page_text)
        if size_match:
            company_size = size_match.group(1).strip()

        # --- Job Description ---
        job_description = self._extract_section(soup, "mô tả công việc")

        # --- Requirements ---
        requirements = self._extract_section(soup, "yêu cầu công việc")
        if requirements:
            if job_description:
                job_description = f"{job_description}\n\n[Yêu cầu]\n{requirements}"
            else:
                job_description = requirements

        # --- Benefits ---
        benefits = self._extract_section(soup, "quyền lợi")

        # --- Skills ---
        skills = self._extract_detail_skills(soup, page_text)

        return {
            "job_title": job_title,
            "company_name": company_name,
            "company_size": company_size,
            "location": "",
            "salary_min": None,
            "salary_max": None,
            "salary_currency": "VND",
            "experience_required": experience_required,
            "skills": skills,
            "job_type": job_type,
            "job_level": job_level,
            "posted_date": None,
            "deadline": None,
            "job_description": job_description or "",
            "benefits": benefits or "",
            "source": "careerviet",
        }

    # ------------------------------------------------------------------
    # Section extraction
    # ------------------------------------------------------------------

    def _extract_section(self, soup: BeautifulSoup, section_name: str) -> Optional[str]:
        """Extract a section's content from the page by heading text."""
        section_lower = section_name.lower()

        for heading in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
            heading_text = heading.get_text(strip=True).lower()
            if section_lower in heading_text:
                content_parts = []
                sibling = heading.find_next_sibling()
                while sibling:
                    if sibling.name in ["h2", "h3", "h4"]:
                        break
                    text = sibling.get_text(strip=True)
                    if text:
                        content_parts.append(text)
                    sibling = sibling.find_next_sibling()

                if content_parts:
                    return "\n".join(content_parts)

                # Try parent's next sibling
                parent = heading.parent
                if parent:
                    next_el = parent.find_next_sibling()
                    if next_el:
                        text = next_el.get_text(separator="\n", strip=True)
                        if text and len(text) > 20:
                            return text

        return None

    def _extract_detail_skills(self, soup: BeautifulSoup, page_text: str) -> List[str]:
        """Extract skills from the detail page."""
        skills: List[str] = []

        # Primary: div.job-tags > ul > li > a
        job_tags = soup.select_one("div.job-tags")
        if job_tags:
            for link in job_tags.select("ul li a"):
                skill = link.get_text(strip=True)
                if skill and skill not in skills and len(skill) < 60:
                    skills.append(skill)

        return skills

    # ------------------------------------------------------------------
    # Parsing utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_salary(text: Optional[str]) -> Tuple[Optional[float], Optional[float], str]:
        """Extract (salary_min, salary_max, currency) from salary string."""
        if not text:
            return None, None, "VND"

        text_lower = text.lower().strip()

        # Negotiable / competitive
        if any(kw in text_lower for kw in [
            "cạnh tranh", "canh tranh", "thỏa thuận",
            "thoả thuận", "thương lượng",
        ]):
            return None, None, "VND"

        # Determine currency
        currency = "VND"
        if "usd" in text_lower or "$" in text:
            currency = "USD"

        # Determine multiplier
        multiplier = 1.0
        if re.search(r"\btr\b|triệu", text_lower):
            multiplier = 1_000_000.0

        # Extract numbers
        if currency == "USD" and multiplier == 1.0:
            # USD with dots as thousand separators: "1.200 - 1.600 USD"
            numbers = re.findall(r"(\d[\d.]*)", text)
            parsed_nums = []
            for n in numbers:
                n_clean = n.replace(".", "")
                try:
                    parsed_nums.append(float(n_clean))
                except ValueError:
                    continue
        else:
            # VND with Tr: "6,8 Tr - 10 Tr" or "12 Tr - 16 Tr"
            numbers = re.findall(r"(\d+[.,]?\d*)", text)
            parsed_nums = []
            for n in numbers:
                n_clean = n.replace(",", ".")
                try:
                    parsed_nums.append(float(n_clean) * multiplier)
                except ValueError:
                    continue

        if not parsed_nums:
            return None, None, currency

        if len(parsed_nums) >= 2:
            return min(parsed_nums), max(parsed_nums), currency

        val = parsed_nums[0]
        if any(kw in text_lower for kw in ["lên đến", "tới", "đến", "to"]):
            return None, val, currency
        elif any(kw in text_lower for kw in ["từ", "tu"]):
            return val, None, currency
        else:
            return val, val, currency

    @staticmethod
    def _parse_experience(text: Optional[str]) -> Optional[float]:
        """Extract numeric years of experience from text."""
        if not text:
            return None
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["không", "khong", "chưa"]):
            return 0.0
        match = re.search(r"(\d+)", text)
        return float(match.group(1)) if match else None

    @staticmethod
    def _parse_date(text: Optional[str]) -> Optional[str]:
        """Parse a date string into ISO format (YYYY-MM-DD)."""
        if not text:
            return None
        text = text.strip()
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        match = re.search(r"(\d{2}[-/]\d{2}[-/]\d{4})", text)
        if match:
            date_str = match.group(1).replace("/", "-")
            try:
                return datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")
            except ValueError:
                pass
        return None

    # ------------------------------------------------------------------
    # Record merging
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_records(listing: dict, detail: dict) -> dict:
        """Merge detail page data into listing page data.

        Listing data takes priority for fields already populated.
        """
        merged = listing.copy()

        for key, value in detail.items():
            if key.startswith("_"):
                continue
            existing = merged.get(key)
            if value and (existing is None or existing == "" or existing == []):
                merged[key] = value

        # Combine skills from both sources
        listing_skills = listing.get("skills", [])
        detail_skills = detail.get("skills", [])
        if detail_skills:
            combined = list(listing_skills)
            for s in detail_skills:
                if s not in combined:
                    combined.append(s)
            merged["skills"] = combined

        return merged
