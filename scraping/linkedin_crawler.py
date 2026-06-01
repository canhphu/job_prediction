"""LinkedIn crawler for collecting IT job listings via public guest API.

Crawls job listings from LinkedIn Jobs using the public guest API endpoints
that do not require authentication. Extracts job data from HTML responses
using BeautifulSoup.

Endpoints used:
- Listing: /jobs-guest/jobs/api/seeMoreJobPostings/search
- Detail: /jobs-guest/jobs/api/jobPosting/{job_id}
"""

import re
from datetime import datetime, timedelta
from typing import List, Optional

from bs4 import BeautifulSoup

from scraping.base_crawler import BaseCrawler
from src.utils.logger import get_logger

logger = get_logger(__name__)

# LinkedIn public guest API endpoints
BASE_URL = "https://www.linkedin.com"
LISTING_API = "/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_API = "/jobs-guest/jobs/api/jobPosting"

# Default search parameters
DEFAULT_KEYWORDS = "IT"
DEFAULT_GEO_ID = "104195383"  # Vietnam


class LinkedInCrawler(BaseCrawler):
    """Crawler for LinkedIn job listings via public guest API.

    Uses LinkedIn's public (no-auth) guest API to fetch job listings
    and detail pages. Returns HTML that can be parsed with BeautifulSoup.

    Parameters
    ----------
    keywords : str
        Search keywords for job listings.
    geo_id : str
        LinkedIn geo ID for location filtering (104195383 = Vietnam).
    location : str
        Location text for the search query.
    delay : float
        Minimum seconds between requests.
    max_retries : int
        Maximum retry attempts for transient network errors.
    """

    def __init__(
        self,
        keywords: str = DEFAULT_KEYWORDS,
        geo_id: str = DEFAULT_GEO_ID,
        location: str = "Vietnam",
        delay: float = 3.0,
        max_retries: int = 3,
    ):
        super().__init__(source_name="linkedin", delay=delay, max_retries=max_retries)
        self.keywords = keywords
        self.geo_id = geo_id
        self.location = location
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def crawl(self, max_pages: Optional[int] = None) -> List[dict]:
        """Crawl LinkedIn IT job listings via public guest API.

        Parameters
        ----------
        max_pages : int | None
            Maximum number of result pages to crawl (10 jobs per page).
            ``None`` means crawl until no more results.

        Returns
        -------
        list[dict]
            List of Job_Record dictionaries with all 16 fields.
        """
        self._start_session()
        records: List[dict] = []

        page = 0
        page_count = 0
        per_page = 10  # LinkedIn guest API returns 10 per request

        while max_pages is None or page_count < max_pages:
            start = page * per_page
            logger.info(
                "Crawling LinkedIn page %d (start=%d)", page_count + 1, start
            )

            job_ids = self._fetch_job_list(start=start)
            if not job_ids:
                logger.info("No more jobs found at offset %d — finished", start)
                break

            self._total_pages += 1
            page_count += 1

            for job_id in job_ids:
                record = self._fetch_and_parse_detail(job_id)
                if record is not None:
                    records.append(record)
                    self._total_records += 1

            # If fewer results than expected, we've reached the end
            if len(job_ids) < per_page:
                logger.info(
                    "Last page reached (got %d < %d)", len(job_ids), per_page
                )
                break

            page += 1

        self._end_session()
        logger.info("LinkedIn crawl complete: %d records collected", len(records))
        return records

    # ------------------------------------------------------------------
    # Listing page
    # ------------------------------------------------------------------

    def _fetch_job_list(self, start: int = 0) -> List[str]:
        """Fetch a page of job IDs from LinkedIn guest search API.

        Parameters
        ----------
        start : int
            Offset for pagination.

        Returns
        -------
        list[str]
            List of job posting IDs (numeric strings).
        """
        url = (
            f"{BASE_URL}{LISTING_API}"
            f"?keywords={self.keywords}"
            f"&location={self.location}"
            f"&geoId={self.geo_id}"
            f"&start={start}"
        )

        response = self.fetch_with_retry(url, headers=self._headers)
        if response is None:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        job_ids: List[str] = []

        # Each job card has data-entity-urn="urn:li:jobPosting:{id}"
        for card in soup.select("div[data-entity-urn]"):
            urn = card.get("data-entity-urn", "")
            # Extract numeric ID from URN
            match = re.search(r"jobPosting:(\d+)", urn)
            if match:
                job_ids.append(match.group(1))

        logger.info("Found %d job IDs on this page", len(job_ids))
        return job_ids

    # ------------------------------------------------------------------
    # Detail page
    # ------------------------------------------------------------------

    def _fetch_and_parse_detail(self, job_id: str) -> Optional[dict]:
        """Fetch and parse a single job detail page.

        Parameters
        ----------
        job_id : str
            Numeric job posting ID.

        Returns
        -------
        dict | None
            A Job_Record dictionary, or None on failure.
        """
        url = f"{BASE_URL}{DETAIL_API}/{job_id}"

        response = self.fetch_with_retry(url, headers=self._headers)
        if response is None:
            return None

        try:
            return self._parse_detail_page(response.text, job_id)
        except Exception as exc:
            logger.error("Error parsing job %s: %s", job_id, exc)
            return None

    def _parse_detail_page(self, html: str, job_id: str) -> dict:
        """Parse a LinkedIn guest job detail page into a Job_Record.

        The guest detail page has a consistent structure with:
        - h2.top-card-layout__title -> job title
        - a.topcard__org-name-link -> company name
        - span.topcard__flavor--bullet -> location
        - li.description__job-criteria-item -> seniority, type, function, industry
        - div.description__text -> full job description

        Parameters
        ----------
        html : str
            Raw HTML of the detail page.
        job_id : str
            Job ID for reference.

        Returns
        -------
        dict
            Job_Record with all 16 fields.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Job title
        job_title = self._text(soup, "h2.top-card-layout__title")

        # Company name
        company_name = self._text(soup, "a.topcard__org-name-link")
        if not company_name:
            company_name = self._text(soup, "span.topcard__flavor")

        # Location
        location = self._text(soup, "span.topcard__flavor--bullet")

        # Job criteria (seniority, employment type, function, industry)
        criteria = self._parse_criteria(soup)
        job_level = criteria.get("Seniority level", "")
        job_type = criteria.get("Employment type", "")
        job_function = criteria.get("Job function", "")
        industries = criteria.get("Industries", "")

        # Full description
        desc_el = soup.select_one("div.description__text")
        job_description = ""
        if desc_el:
            # Remove the "Show more" button text
            for btn in desc_el.select("button"):
                btn.decompose()
            job_description = desc_el.get_text(separator="\n", strip=True)

        # Company size - try to extract from page
        company_size = self._extract_company_size(soup)

        # Salary - extract from description or criteria
        salary_min, salary_max, salary_currency = self._parse_salary_from_text(
            job_description
        )

        # Experience
        experience_required = self._parse_experience(job_description)

        # Skills
        skills = self._extract_skills(job_description)

        # Posted date
        posted_date = self._parse_posted_date(soup)

        # Benefits
        benefits = self._extract_benefits(job_description)

        return {
            "job_title": job_title or "",
            "company_name": company_name or "",
            "company_size": company_size,
            "location": location or "",
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "experience_required": experience_required,
            "skills": skills,
            "job_type": job_type,
            "job_level": job_level,
            "posted_date": posted_date,
            "deadline": None,  # LinkedIn doesn't show deadlines publicly
            "job_description": job_description,
            "benefits": benefits,
            "source": "linkedin",
        }

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _text(soup: BeautifulSoup, selector: str) -> Optional[str]:
        """Get stripped text from first element matching selector."""
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    @staticmethod
    def _parse_criteria(soup: BeautifulSoup) -> dict:
        """Parse job criteria items into a dict.

        Each criteria item has:
        - h3 header (e.g. "Seniority level")
        - span value (e.g. "Mid-Senior level")
        """
        criteria = {}
        for item in soup.select("li.description__job-criteria-item"):
            header_el = item.select_one("h3")
            value_el = item.select_one("span")
            if header_el and value_el:
                key = header_el.get_text(strip=True)
                value = value_el.get_text(strip=True)
                criteria[key] = value
        return criteria

    @staticmethod
    def _extract_company_size(soup: BeautifulSoup) -> Optional[str]:
        """Try to extract company size from the page."""
        # Guest pages sometimes show company info
        for el in soup.select("span.num-applicants__caption"):
            text = el.get_text(strip=True)
            if "employee" in text.lower():
                return text
        return None

    @staticmethod
    def _parse_salary_from_text(text: str) -> tuple:
        """Extract salary range from description text.

        Returns (min, max, currency) tuple.
        """
        if not text:
            return None, None, None

        # Common salary patterns
        patterns = [
            # $1,000 - $2,000 or $1000-$2000
            r"\$\s*([\d,]+)\s*[-–to]+\s*\$\s*([\d,]+)",
            # 1000 - 2000 USD
            r"([\d,]+)\s*[-–to]+\s*([\d,]+)\s*(USD|VND|EUR)",
            # VND 10,000,000 - 20,000,000
            r"(VND|USD)\s*([\d,]+)\s*[-–to]+\s*([\d,]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    # $min - $max
                    min_val = float(groups[0].replace(",", ""))
                    max_val = float(groups[1].replace(",", ""))
                    return min_val, max_val, "USD"
                elif len(groups) == 3:
                    if groups[0] in ("USD", "VND", "EUR"):
                        # Currency first
                        currency = groups[0]
                        min_val = float(groups[1].replace(",", ""))
                        max_val = float(groups[2].replace(",", ""))
                    else:
                        # Currency last
                        min_val = float(groups[0].replace(",", ""))
                        max_val = float(groups[1].replace(",", ""))
                        currency = groups[2]
                    return min_val, max_val, currency

        return None, None, None

    @staticmethod
    def _parse_experience(text: str) -> Optional[float]:
        """Extract years of experience from description."""
        if not text:
            return None

        patterns = [
            r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)",
            r"(?:experience|exp)\s*(?:of\s+)?(\d+)\+?\s*(?:years?|yrs?)",
            r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:relevant|professional|working)",
            r"(\d+)\s*[-–]\s*\d+\s*(?:years?|yrs?)",
            r"(?:at least|minimum)\s*(\d+)\s*(?:years?|yrs?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return None

    @staticmethod
    def _extract_skills(description: str) -> List[str]:
        """Extract skill keywords from job description."""
        if not description:
            return []

        known_skills = [
            "Python", "Java", "JavaScript", "TypeScript", "C++", "C#",
            "Go", "Golang", "Rust", "Ruby", "PHP", "Swift", "Kotlin",
            "Scala", "R", "MATLAB", "Perl",
            "React", "Angular", "Vue", "Vue.js", "Next.js", "Nuxt",
            "Node.js", "Express", "Django", "Flask", "FastAPI",
            "Spring", "Spring Boot", ".NET", "ASP.NET", "Laravel",
            "Docker", "Kubernetes", "K8s", "AWS", "Azure", "GCP",
            "Terraform", "Ansible", "Jenkins", "GitLab CI", "GitHub Actions",
            "SQL", "NoSQL", "MongoDB", "PostgreSQL", "MySQL", "Redis",
            "Elasticsearch", "Kibana", "Kafka", "RabbitMQ",
            "Git", "CI/CD", "DevOps", "Agile", "Scrum",
            "Linux", "Unix", "Windows Server",
            "REST", "RESTful", "GraphQL", "gRPC", "Microservices",
            "Machine Learning", "Deep Learning", "NLP", "AI",
            "TensorFlow", "PyTorch", "Pandas", "NumPy",
            "HTML", "CSS", "SASS", "Tailwind",
            "Power BI", "Tableau", "Excel",
            "Jira", "Confluence", "Slack",
            "Figma", "Sketch", "Adobe",
            "Selenium", "Cypress", "Jest", "JUnit",
            "API", "SDK", "OAuth", "JWT",
            "Blockchain", "Web3", "Solidity",
            "iOS", "Android", "React Native", "Flutter",
            "SAP", "Salesforce", "ServiceNow",
            "ITIL", "ITSM", "Active Directory",
            "VMware", "Hyper-V", "Networking",
            "Firewall", "VPN", "Security", "Cybersecurity",
        ]

        found_skills = []
        desc_lower = description.lower()
        for skill in known_skills:
            # Use word boundary check for short skills
            if len(skill) <= 3:
                if re.search(r"\b" + re.escape(skill) + r"\b", description, re.IGNORECASE):
                    found_skills.append(skill)
            else:
                if skill.lower() in desc_lower:
                    found_skills.append(skill)

        return list(dict.fromkeys(found_skills))  # deduplicate preserving order

    @staticmethod
    def _parse_posted_date(soup: BeautifulSoup) -> Optional[str]:
        """Extract and parse the posted date from the page.

        LinkedIn shows relative dates like "2 weeks ago" or absolute
        dates in a time element.
        """
        # Try datetime attribute on time element
        time_el = soup.select_one("span.posted-time-ago__text")
        if not time_el:
            time_el = soup.select_one("span.topcard__flavor--metadata")

        if time_el:
            # Check for datetime attribute
            parent_time = time_el.find_parent("time")
            if parent_time and parent_time.get("datetime"):
                return parent_time["datetime"][:10]  # YYYY-MM-DD

            text = time_el.get_text(strip=True)
            return LinkedInCrawler._relative_date_to_iso(text)

        return None

    @staticmethod
    def _relative_date_to_iso(text: str) -> Optional[str]:
        """Convert relative date text to ISO format.

        Examples: "2 weeks ago", "3 days ago", "1 month ago"
        """
        if not text:
            return None

        now = datetime.now()
        text_lower = text.lower().strip()

        patterns = [
            (r"(\d+)\s*minute", "minutes"),
            (r"(\d+)\s*hour", "hours"),
            (r"(\d+)\s*day", "days"),
            (r"(\d+)\s*week", "weeks"),
            (r"(\d+)\s*month", "months"),
        ]

        for pattern, unit in patterns:
            match = re.search(pattern, text_lower)
            if match:
                value = int(match.group(1))
                if unit == "minutes":
                    delta = timedelta(minutes=value)
                elif unit == "hours":
                    delta = timedelta(hours=value)
                elif unit == "days":
                    delta = timedelta(days=value)
                elif unit == "weeks":
                    delta = timedelta(weeks=value)
                elif unit == "months":
                    delta = timedelta(days=value * 30)
                else:
                    continue
                return (now - delta).strftime("%Y-%m-%d")

        # "Just now" or "Today"
        if "just" in text_lower or "today" in text_lower:
            return now.strftime("%Y-%m-%d")

        return text  # Return as-is if can't parse

    @staticmethod
    def _extract_benefits(description: str) -> Optional[str]:
        """Extract benefits/perks section from job description."""
        if not description:
            return None

        # Look for common benefit section headers
        # Use non-backtracking approach: find header, then take text until next section
        headers_pattern = r"(?:What We Offer|Benefits|Perks|What we offer|Our Benefits|Why join us)[:\s]*\n"
        match = re.search(headers_pattern, description, re.IGNORECASE)
        if not match:
            return None

        # Take text from after the header
        rest = description[match.end():]

        # Find the next section header or end
        end_patterns = [
            r"\n(?:The hiring|How to apply|Apply|Requirements|About You|Qualifications|Responsibilities|About Us|Job Description)",
            r"\n\n\n",  # Triple newline as section break
        ]
        end_pos = len(rest)
        for ep in end_patterns:
            m = re.search(ep, rest, re.IGNORECASE)
            if m and m.start() < end_pos:
                end_pos = m.start()

        benefits_text = rest[:end_pos].strip()
        if len(benefits_text) > 50:
            if len(benefits_text) > 1000:
                benefits_text = benefits_text[:1000] + "..."
            return benefits_text

        return None
