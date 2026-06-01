"""ITviec crawler"""

import json
import re
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from bs4 import BeautifulSoup, Tag

from scraping.base_crawler import BaseCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Default base URL and listing path for ITviec
BASE_URL = "https://itviec.com"
LISTING_PATH = "/it-jobs"


class ITviecCrawler(BaseCrawler):
    """Crawler for ITviec (itviec.com) IT job listings.

    Parameters
    ----------
    base_url : str
        Root URL of the ITviec site.
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
        super().__init__(source_name="itviec", delay=delay, max_retries=max_retries)
        self.base_url = base_url.rstrip("/")
        self._session: Optional[requests.Session] = None
        self._logged_in: bool = False

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> bool:
        """Login to ITviec to access salary data.

        Parameters
        ----------
        email : str
            ITviec account email.
        password : str
            ITviec account password.

        Returns
        -------
        bool
            True if login was successful, False otherwise.
        """
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        })

        try:
            # Step 1: GET /sign_in to get CSRF token
            login_url = f"{self.base_url}/sign_in"
            resp = self._session.get(login_url, timeout=30)
            if resp.status_code != 200:
                logger.error("Failed to load login page: HTTP %d", resp.status_code)
                return False

            soup = BeautifulSoup(resp.text, "html.parser")
            # Find the email/password form (action="/sign_in")
            form = soup.find("form", action="/sign_in")
            if not form:
                logger.error("Login form not found on page")
                return False

            # Extract CSRF token
            token_input = form.find("input", {"name": "authenticity_token"})
            if not token_input:
                logger.error("CSRF token not found in login form")
                return False
            csrf_token = token_input.get("value", "")

            # Step 2: POST /sign_in with credentials
            login_data = {
                "authenticity_token": csrf_token,
                "user[email]": email,
                "user[password]": password,
                "locale": "en",
            }

            resp = self._session.post(
                login_url,
                data=login_data,
                timeout=30,
                allow_redirects=True,
            )

            # Check if login succeeded (redirects to home or dashboard)
            if resp.status_code == 200 and "/sign_in" not in resp.url:
                self._logged_in = True
                logger.info("Login thành công với email: %s", email)
                return True

            # Check for error messages in response
            if "Invalid Email or password" in resp.text:
                logger.error("Login thất bại: Email hoặc mật khẩu không đúng")
            else:
                logger.error("Login thất bại: status=%d, url=%s", resp.status_code, resp.url)

            return False

        except requests.RequestException as exc:
            logger.error("Login error: %s", exc)
            return False

    def fetch_with_retry(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Override to use session if logged in."""
        if self._session and self._logged_in:
            return self._fetch_with_session(url, **kwargs)
        return super().fetch_with_retry(url, **kwargs)

    def _fetch_with_session(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Fetch URL using the authenticated session with retry logic."""
        from src.utils.data_reports import CrawlError

        self._wait_for_delay(url)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self._session.get(url, timeout=30, **kwargs)

                if response.status_code >= 400:
                    error = CrawlError(
                        url=url,
                        error_code=response.status_code,
                        timestamp=datetime.now(),
                        message=f"HTTP {response.status_code}",
                    )
                    self._errors.append(error)
                    logger.error("HTTP error %d for %s", response.status_code, url)
                    return None

                return response

            except requests.RequestException as exc:
                backoff = 2 ** attempt
                error = CrawlError(
                    url=url,
                    error_code=0,
                    timestamp=datetime.now(),
                    message=str(exc),
                )
                self._errors.append(error)
                logger.error(
                    "Network error (attempt %d/%d) for %s: %s",
                    attempt, self.max_retries, url, exc,
                )

                if attempt < self.max_retries:
                    import time
                    time.sleep(backoff)
                else:
                    logger.error("All retries exhausted for %s", url)

        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def crawl(self, max_pages: Optional[int] = None) -> List[dict]:
        """Crawl ITviec IT job listings.

        Parameters
        ----------
        max_pages : int | None
            Maximum number of listing pages to crawl.  ``None`` means
            crawl until no more pages are found.

        Returns
        -------
        list[dict]
            List of Job_Record dictionaries with all 16 fields.
        """
        self._start_session()
        records: List[dict] = []

        # Check robots.txt before starting
        if not self.check_robots_txt(self.base_url):
            logger.warning("ITviec robots.txt disallows crawling — aborting")
            self._end_session()
            return records

        page = 1
        while max_pages is None or page <= max_pages:
            page_url = f"{self.base_url}{LISTING_PATH}?page={page}"
            logger.info("Crawling ITviec listing page %d: %s", page, page_url)

            response = self.fetch_with_retry(page_url)
            if response is None:
                logger.warning("Failed to fetch listing page %d — stopping", page)
                break

            jobs_on_page = self._parse_listing_page(response.text)
            if not jobs_on_page:
                logger.info("No job cards found on page %d — finished", page)
                break

            self._total_pages += 1

            for job_data in jobs_on_page:
                # Optionally fetch detail page for additional info
                detail_url = job_data.get("_detail_url")
                if detail_url:
                    detail_record = self._crawl_detail_page(detail_url)
                    if detail_record:
                        # Merge detail info into listing data
                        job_data = self._merge_records(job_data, detail_record)

                records.append(job_data)
                self._total_records += 1

            page += 1

        # Clean up internal fields from all records
        for record in records:
            record.pop("_detail_url", None)

        self._end_session()
        logger.info("ITviec crawl complete: %d records collected", len(records))
        return records

    def enrich_salary_via_filters(self, records: List[dict], max_pages_per_range: int = 5) -> List[dict]:
        """Enrich salary data by crawling with salary range filters.

        Parameters
        ----------
        records : list[dict]
            Existing records (some may already have salary data).
        max_pages_per_range : int
            Max pages to crawl per salary range (default 5).

        Returns
        -------
        list[dict]
            Updated records with salary_min/salary_max filled where possible.
        """
        # Only enrich records that don't have salary
        needs_salary = [r for r in records if r.get("salary_min") is None and r.get("salary_max") is None]
        if not needs_salary:
            logger.info("All records already have salary data — skipping filter enrichment")
            return records

        # Collect all job slugs that need salary
        slug_to_idx = {}
        for i, r in enumerate(records):
            if r.get("salary_min") is None and r.get("salary_max") is None:
                # Extract slug from source URL or job_title
                slug = r.get("_slug", "")
                if slug:
                    slug_to_idx[slug] = i

        if not slug_to_idx:
            return records

        logger.info("Enriching salary for %d jobs via salary range filters...", len(slug_to_idx))

        # Define salary ranges (USD, non-overlapping brackets)
        salary_ranges = [
            (500, 1000),
            (1000, 1500),
            (1500, 2000),
            (2000, 3000),
            (3000, 5000),
            (5000, 10000),
        ]

        for range_min, range_max in salary_ranges:
            if not slug_to_idx:
                break  # All jobs enriched

            logger.info("  Checking salary range $%d - $%d...", range_min, range_max)
            slugs_in_range = self._get_slugs_in_salary_range(
                range_min, range_max, max_pages=max_pages_per_range
            )

            # Match found slugs to our records
            matched = set(slug_to_idx.keys()) & slugs_in_range
            for slug in matched:
                idx = slug_to_idx[slug]
                records[idx]["salary_min"] = float(range_min)
                records[idx]["salary_max"] = float(range_max)
                logger.debug("  Enriched '%s' with salary $%d-$%d", slug[:40], range_min, range_max)

            # Remove matched slugs from pending
            for slug in matched:
                del slug_to_idx[slug]

            enriched_count = len(matched)
            if enriched_count:
                logger.info("    Found %d jobs in $%d-$%d range", enriched_count, range_min, range_max)

        total_enriched = len(needs_salary) - len(slug_to_idx)
        logger.info("Salary enrichment complete: %d/%d jobs enriched", total_enriched, len(needs_salary))
        return records

    def _get_slugs_in_salary_range(
        self, salary_min: int, salary_max: int, max_pages: int = 5
    ) -> set:
        """Get all job slugs that appear in a given salary range filter.

        Parameters
        ----------
        salary_min : int
            Minimum salary (USD).
        salary_max : int
            Maximum salary (USD).
        max_pages : int
            Maximum pages to crawl for this range.

        Returns
        -------
        set[str]
            Set of job slugs found in this salary range.
        """
        slugs = set()

        for page in range(1, max_pages + 1):
            url = (
                f"{self.base_url}{LISTING_PATH}"
                f"?salary_ranges[]={salary_min}"
                f"&salary_ranges[]={salary_max}"
                f"&salary_ranges_changed=true"
                f"&page={page}"
            )

            response = self.fetch_with_retry(url)
            if response is None:
                break

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.select("div.job-card")

            if not cards:
                break

            for card in cards:
                slug = card.get("data-search--job-selection-job-slug-value", "")
                if slug:
                    slugs.add(slug)

        return slugs

    # ------------------------------------------------------------------
    # Listing page parsing
    # ------------------------------------------------------------------

    def _parse_listing_page(self, html: str) -> List[dict]:
        """Extract job records from an ITviec listing page.

        Parameters
        ----------
        html : str
            Raw HTML of the listing page.

        Returns
        -------
        list[dict]
            List of partially-filled Job_Record dicts (with an extra
            ``_detail_url`` key for optional detail page fetching).
        """
        soup = BeautifulSoup(html, "html.parser")
        jobs: List[dict] = []

        # ITviec job cards use class "job-card"
        job_cards = soup.select("div.job-card")

        for card in job_cards:
            job = self._parse_job_card(card)
            if job and job.get("job_title"):
                jobs.append(job)

        return jobs

    def _parse_job_card(self, card: Tag) -> Optional[dict]:
        """Parse a single job card element into a Job_Record dict.

        Parameters
        ----------
        card : Tag
            BeautifulSoup Tag representing a div.job-card element.

        Returns
        -------
        dict | None
            Partially-filled Job_Record dict, or None if parsing fails.
        """
        try:
            # --- Job title ---
            # h3 with data-search--job-selection-target="jobTitle"
            title_el = card.select_one('h3[data-search--job-selection-target="jobTitle"]')
            if not title_el:
                title_el = card.select_one("h3")
            job_title = title_el.get_text(strip=True) if title_el else ""

            # --- Detail URL from data attribute ---
            job_slug = card.get("data-search--job-selection-job-slug-value", "")
            detail_url = f"{self.base_url}/it-jobs/{job_slug}" if job_slug else None

            # --- Company name ---
            company_name = self._extract_company_name(card)

            # --- Salary ---
            salary_text = self._extract_salary_text(card)
            salary_min, salary_max = self._parse_salary(salary_text)

            # Fallback: try to parse salary from job title
            if salary_min is None and salary_max is None and job_title:
                salary_min, salary_max = self._parse_salary_from_title(job_title)

            # --- Location ---
            location = self._extract_location(card)

            # --- Skills ---
            skills = self._extract_skills(card)

            # --- Job level ---
            job_level = self._extract_job_level(card)

            # --- Expertise/role (job type) ---
            job_type = self._extract_expertise(card)

            # --- Working model ---
            working_model = self._extract_working_model(card)

            # --- Posted date ---
            posted_date = self._extract_posted_date(card)

            # --- Benefits ---
            benefits = self._extract_benefits(card)

            # Combine working model and expertise into job_type field
            type_parts = [p for p in [working_model, job_type] if p]
            combined_type = " | ".join(type_parts) if type_parts else ""

            return {
                "job_title": job_title,
                "company_name": company_name or "",
                "company_size": None,  # Available on company detail page
                "location": location or "",
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": "USD",  # ITviec typically lists in USD
                "experience_required": None,  # Available on detail page
                "skills": skills,
                "job_type": combined_type,
                "job_level": job_level or "",
                "posted_date": posted_date,
                "deadline": None,  # Not shown on listing page
                "job_description": "",  # Available on detail page
                "benefits": benefits or "",
                "source": "itviec",
                "_detail_url": detail_url,
                "_slug": job_slug,
            }
        except Exception as exc:
            logger.debug("Error parsing job card: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    def _extract_company_name(self, card: Tag) -> Optional[str]:
        """Extract company name from a job card."""
        for link in card.find_all("a", href=True):
            href = link.get("href", "")
            if "/companies/" in href:
                text = link.get_text(strip=True)
                if text:
                    return text
        return None

    def _extract_salary_text(self, card: Tag) -> Optional[str]:
        """Extract salary text from a job card."""
        # Check for salary container
        salary_div = card.select_one("div.salary")
        if salary_div:
            text = salary_div.get_text(strip=True)
            if "Sign in" in text:
                return None
            # Look for dollar amounts (range)
            salary_match = re.search(r"\$[\d,]+\s*[-–]\s*\$[\d,]+", text)
            if salary_match:
                return salary_match.group(0)
            # "Up to $X" or "Lên đến $X"
            salary_match = re.search(r"(?:[Uu]p\s*to|Lên đến)\s*\$[\d,]+", text)
            if salary_match:
                return salary_match.group(0)
            # Single amount "$X"
            salary_match = re.search(r"\$[\d,]+", text)
            if salary_match:
                return salary_match.group(0)
            # "You'll love it" means hidden
            if "love it" in text.lower():
                return None
            # Any remaining text with numbers might be salary
            if re.search(r"\d", text):
                return text

        # Fallback: check sign-in link
        sign_in = card.select_one("a.sign-in-view-salary")
        if sign_in:
            return None  # Salary hidden behind login

        return None

    def _extract_location(self, card: Tag) -> Optional[str]:
        """Extract job location from a job card."""
        # Strategy 1: Find div with title attribute containing city names
        known_cities = ["Ho Chi Minh", "Ha Noi", "Da Nang", "Others"]
        for div in card.find_all("div", attrs={"title": True}):
            title = div.get("title", "")
            if title in known_cities:
                return title

        # Strategy 2: Look for city text near map-pin icon
        text = card.get_text()
        locations = []
        for city in known_cities:
            if city in text:
                locations.append(city)

        if locations:
            return " - ".join(locations)

        return None

    def _extract_skills(self, card: Tag) -> List[str]:
        """Extract skill tags from a job card."""
        skills: List[str] = []

        # Primary: find tags with data-responsive-tag-list-target="tag"
        for tag in card.select('a[data-responsive-tag-list-target="tag"]'):
            skill = tag.get_text(strip=True)
            if skill and skill not in skills:
                skills.append(skill)

        # Fallback: find links with click_source=Skill+tag in href
        if not skills:
            for link in card.find_all("a", href=True):
                href = link.get("href", "")
                if "click_source=Skill" in href:
                    skill = link.get_text(strip=True)
                    if skill and skill not in skills:
                        skills.append(skill)

        # Fallback 2: find itag elements (skill badge class)
        if not skills:
            for tag in card.select("a.itag"):
                skill = tag.get_text(strip=True)
                if skill and skill not in skills:
                    skills.append(skill)

        return skills

    def _extract_job_level(self, card: Tag) -> Optional[str]:
        """Extract job level from a job card."""
        # Look for job-level class element
        level_el = card.select_one(".job-level, [class*='level']")
        if level_el:
            text = level_el.get_text(strip=True)
            if text:
                return text

        # Fallback: search text for level keywords
        text = card.get_text()
        level_keywords = ["Senior", "Junior", "Fresher", "Manager"]
        for level in level_keywords:
            if level in text:
                return level

        return None

    def _extract_expertise(self, card: Tag) -> Optional[str]:
        """Extract expertise/role category from a job card."""
        # Find links with title attribute that point to expertise pages
        expertise_slugs = {
            "backend-developer", "fullstack-developer", "frontend-developer",
            "mobile-application-developer", "devops-engineer", "data-engineer",
            "business-analyst", "project-manager", "automation-tester",
            "manual-tester", "software-technical-architect", "solution-architect",
            "systems-engineer-administrator", "game-developer",
            "test-coordinator-qaqc-coordinator", "ai-machine-learning-engineer",
            "erp-consultant", "banking-financial-systems-developer",
            "process-quality-assurance-pqa", "manager",
        }

        for link in card.find_all("a", href=True):
            href = link.get("href", "")
            title = link.get("title", "")
            # Check if this is an expertise link (not a skill tag, not a job detail)
            if "/it-jobs/" in href and title and "click_source" not in href:
                # Verify it's an expertise slug (short path, no company suffix)
                slug = href.replace("/it-jobs/", "").split("?")[0]
                if slug in expertise_slugs or (title and len(slug) > 5 and "-" in slug):
                    return title

        return None

    def _extract_working_model(self, card: Tag) -> Optional[str]:
        """Extract working model from a job card."""
        for div in card.find_all("div", class_=True):
            classes = " ".join(div.get("class", []))
            if "text-rich-grey" in classes:
                text = div.get_text(strip=True)
                if text in ("At office", "Remote", "Hybrid"):
                    return text

        # Fallback: search in card text
        card_text = card.get_text()
        if "Hybrid" in card_text:
            return "Hybrid"
        if "Remote" in card_text:
            return "Remote"
        if "At office" in card_text:
            return "At office"

        return None

    def _extract_posted_date(self, card: Tag) -> Optional[str]:
        """Extract and convert posted date from a job card."""
        # Find the posted time element
        posted_el = card.select_one("span.small-text.text-dark-grey")
        if not posted_el:
            posted_el = card.select_one("span.small-text")

        if posted_el:
            text = posted_el.get_text(strip=True)
        else:
            text = card.get_text()

        # Match "Posted X hours/days/minutes ago"
        match = re.search(r"Posted\s*(\d+)\s*(minute|hour|day|week|month)s?\s*ago", text)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            now = datetime.now()

            if unit == "minute":
                posted = now - timedelta(minutes=amount)
            elif unit == "hour":
                posted = now - timedelta(hours=amount)
            elif unit == "day":
                posted = now - timedelta(days=amount)
            elif unit == "week":
                posted = now - timedelta(weeks=amount)
            elif unit == "month":
                posted = now - timedelta(days=amount * 30)
            else:
                return None

            return posted.strftime("%Y-%m-%d")

        return None

    def _extract_benefits(self, card: Tag) -> Optional[str]:
        """Extract benefits text from a job card."""
        benefits_items = []

        for li in card.find_all("li"):
            text = li.get_text(strip=True)
            if text and len(text) > 5:
                benefits_items.append(text)

        return "; ".join(benefits_items) if benefits_items else None

    # ------------------------------------------------------------------
    # Detail/Company page parsing
    # ------------------------------------------------------------------

    def _crawl_detail_page(self, url: str) -> Optional[dict]:
        """Fetch and parse a single ITviec job detail page.

        Parameters
        ----------
        url : str
            URL of the job detail page.

        Returns
        -------
        dict | None
            Additional fields from the detail page, or ``None`` if the
            page could not be fetched or parsed.
        """
        response = self.fetch_with_retry(url)
        if response is None:
            return None

        try:
            return self._parse_detail_page(response.text, url)
        except Exception as exc:
            logger.error("Error parsing ITviec detail page %s: %s", url, exc)
            return None

    def _parse_detail_page(self, html: str, url: str) -> dict:
        """Parse an ITviec job detail page for additional information.

        Parameters
        ----------
        html : str
            Raw HTML of the detail page.
        url : str
            Source URL (used for logging).

        Returns
        -------
        dict
            Additional fields to merge into the listing record.
        """
        soup = BeautifulSoup(html, "html.parser")

        # --- Extract from JSON-LD (primary source) ---
        job_data = self._extract_jsonld(soup)

        if job_data:
            salary_min, salary_max, salary_currency = self._parse_jsonld_salary(job_data)
            experience_required = self._parse_jsonld_experience(job_data)
            deadline = job_data.get("validThrough")
            description = self._clean_html_text(job_data.get("description", ""))
            benefits = self._clean_html_text(job_data.get("jobBenefits", ""))
            employment_type = job_data.get("employmentType", "")

            # Extract company size from hiringOrganization if available
            company_size = None
            hiring_org = job_data.get("hiringOrganization", {})
            if isinstance(hiring_org, dict):
                company_size = hiring_org.get("numberOfEmployees")

            return {
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": salary_currency or "USD",
                "experience_required": experience_required,
                "deadline": deadline,
                "job_description": description,
                "benefits": benefits,
                "company_size": company_size,
            }

        # --- Fallback: parse HTML directly ---
        company_size = self._extract_company_size(soup)
        job_description = self._extract_job_description(soup)
        experience_required = self._extract_experience(soup)
        benefits = self._extract_full_benefits(soup)

        return {
            "company_size": company_size,
            "job_description": job_description or "",
            "experience_required": experience_required,
            "benefits": benefits or "",
        }

    def _extract_jsonld(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract JobPosting JSON-LD data from the page.

        Returns the parsed dict if found, or None.
        """
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                content = script.string
                if not content:
                    continue
                data = json.loads(content)
                if isinstance(data, dict) and data.get("@type") == "JobPosting":
                    return data
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def _parse_jsonld_salary(self, data: dict) -> tuple:
        """Parse salary from JSON-LD baseSalary field.

        Returns (salary_min, salary_max, currency).
        """
        base_salary = data.get("baseSalary")
        if not base_salary or not isinstance(base_salary, dict):
            return None, None, None

        currency = base_salary.get("currency", "USD")
        value_obj = base_salary.get("value", {})

        if not isinstance(value_obj, dict):
            return None, None, currency

        # Try minValue/maxValue first
        min_val = value_obj.get("minValue")
        max_val = value_obj.get("maxValue")
        if min_val is not None or max_val is not None:
            try:
                salary_min = float(min_val) if min_val is not None else None
                salary_max = float(max_val) if max_val is not None else None
                return salary_min, salary_max, currency
            except (ValueError, TypeError):
                pass

        # Try parsing from "value" string (e.g., "Up to $3000", "$1000 - $2000")
        value_str = str(value_obj.get("value", ""))
        if value_str:
            numbers = re.findall(r"[\d,]+", value_str)
            floats = []
            for n in numbers:
                try:
                    floats.append(float(n.replace(",", "")))
                except ValueError:
                    continue

            if len(floats) >= 2:
                return min(floats), max(floats), currency
            if len(floats) == 1:
                # "Up to X" → max only; "From X" → min only
                if "up to" in value_str.lower():
                    return None, floats[0], currency
                elif "from" in value_str.lower() or "trên" in value_str.lower():
                    return floats[0], None, currency
                else:
                    return floats[0], floats[0], currency

        return None, None, currency

    def _parse_jsonld_experience(self, data: dict) -> Optional[float]:
        """Parse experience from JSON-LD experienceRequirements.

        Returns years as float.
        """
        exp = data.get("experienceRequirements")
        if not exp:
            return None

        if isinstance(exp, dict):
            months = exp.get("monthsOfExperience")
            if months is not None:
                try:
                    return round(float(months) / 12, 1)
                except (ValueError, TypeError):
                    pass

        # Try parsing as string
        if isinstance(exp, str):
            match = re.search(r"(\d+)", exp)
            if match:
                return float(match.group(1))

        return None

    @staticmethod
    def _clean_html_text(html_text: str) -> str:
        """Remove HTML tags from a string and clean up whitespace."""
        if not html_text:
            return ""
        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", " ", html_text)
        # Normalize whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        # Truncate very long descriptions
        if len(clean) > 5000:
            clean = clean[:5000] + "..."
        return clean

    def _extract_company_size(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract company size from the detail/company page."""
        text = soup.get_text()

        # Look for employee count patterns
        match = re.search(r"(\d+[-–]\d+)\s*employees", text)
        if match:
            return match.group(0)

        match = re.search(r"(\d+\+?)\s*employees", text)
        if match:
            return match.group(0)

        return None

    def _extract_job_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract job description from the detail page."""
        # Look for job description section
        selectors = [
            "div.job-description",
            "div[class*='description']",
            "div[class*='job-detail']",
            "section.job-description",
        ]

        for selector in selectors:
            el = soup.select_one(selector)
            if el:
                return el.get_text(strip=True)

        return None

    def _extract_experience(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract years of experience from the detail page."""
        text = soup.get_text()

        # Match patterns like "3+ years", "2-5 years experience"
        match = re.search(r"(\d+)\+?\s*(?:years?|năm)", text, re.IGNORECASE)
        if match:
            return float(match.group(1))

        return None

    def _extract_full_benefits(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract full benefits from the detail page."""
        benefits_items = []

        # Look for the benefits/love working here section
        for heading in soup.find_all(["h2", "h3", "h4", "div"]):
            heading_text = heading.get_text(strip=True)
            if "love working here" in heading_text.lower() or "benefits" in heading_text.lower():
                # Get the next sibling or parent's list items
                container = heading.find_next(["ul", "ol", "div"])
                if container:
                    for li in container.find_all("li"):
                        text = li.get_text(strip=True)
                        if text:
                            benefits_items.append(text)
                break

        return "; ".join(benefits_items) if benefits_items else None

    # ------------------------------------------------------------------
    # Merge listing + detail data
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_records(listing: dict, detail: dict) -> dict:
        """Merge detail page data into listing page data."""
        merged = dict(listing)
        for key, value in detail.items():
            if key.startswith("_"):
                continue
            # Only override if listing value is empty/None
            if value and (not merged.get(key)):
                merged[key] = value
        return merged

    # ------------------------------------------------------------------
    # Parsing utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Return stripped text of the first element matching *selector*."""
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    @staticmethod
    def _parse_salary(text: Optional[str]) -> tuple:
        """Attempt to extract (salary_min, salary_max) from a salary string"""
        if not text or "love it" in text.lower() or "thỏa thuận" in text.lower():
            return None, None
        if "sign in" in text.lower():
            return None, None

        numbers = re.findall(r"[\d,]+", text)
        floats = []
        for n in numbers:
            try:
                floats.append(float(n.replace(",", "")))
            except ValueError:
                continue

        if len(floats) >= 2:
            return min(floats), max(floats)
        if len(floats) == 1:
            return floats[0], floats[0]
        return None, None

    @staticmethod
    def _parse_salary_from_title(title: str) -> tuple:
        """Extract salary hints from job title text."""
        if not title:
            return None, None

        # Pattern 1: "$X - $Y" or "$X-$Y" or "$X ~ $Y"
        match = re.search(r"\$\s*([\d,]+)\s*[-–~]\s*\$\s*([\d,]+)", title)
        if match:
            try:
                val1 = float(match.group(1).replace(",", ""))
                val2 = float(match.group(2).replace(",", ""))
                return min(val1, val2), max(val1, val2)
            except ValueError:
                pass

        # Pattern 2: "Up to $X" or "~Up to $X" or "up to $X"
        match = re.search(r"[Uu]p\s*to\s*\$\s*([\d,]+)", title)
        if match:
            try:
                val = float(match.group(1).replace(",", ""))
                return None, val
            except ValueError:
                pass

        # Pattern 3: "(~$X)" or "~$X" — approximate salary
        match = re.search(r"~\s*\$\s*([\d,]+)", title)
        if match:
            try:
                val = float(match.group(1).replace(",", ""))
                return val, val
            except ValueError:
                pass

        # Pattern 4: "> $X" or ">$X" — minimum salary
        match = re.search(r">\s*\$\s*([\d,]+)", title)
        if match:
            try:
                val = float(match.group(1).replace(",", ""))
                return val, None
            except ValueError:
                pass

        # Pattern 5: "X$-Y$" or "X$ - Y$" (number before dollar sign)
        match = re.search(r"([\d,]+)\s*\$\s*[-–~]\s*([\d,]+)\s*\$", title)
        if match:
            try:
                val1 = float(match.group(1).replace(",", ""))
                val2 = float(match.group(2).replace(",", ""))
                return min(val1, val2), max(val1, val2)
            except ValueError:
                pass

        return None, None

    @staticmethod
    def _parse_experience(text: Optional[str]) -> Optional[float]:
        """Extract numeric years of experience from a text string."""
        if not text:
            return None

        match = re.search(r"(\d+)", text)
        return float(match.group(1)) if match else None

    @staticmethod
    def _parse_date(text: Optional[str]) -> Optional[str]:
        """Try to parse a date string into ISO format (YYYY-MM-DD).

        Returns the original string if parsing fails, or ``None`` if
        the input is empty.
        """
        if not text:
            return None

        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%B %d, %Y"):
            try:
                return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return text

    @staticmethod
    def _extract_skills_from_tags(soup: BeautifulSoup) -> List[str]:
        """Extract skill names from tag/badge elements on the page."""
        skills: List[str] = []
        for tag in soup.select("div.tag-list a, span.skill-tag"):
            skill = tag.get_text(strip=True)
            if skill:
                skills.append(skill)
        return skills
