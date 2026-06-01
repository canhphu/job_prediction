"""Data models for crawl reporting"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass
class CrawlError:
    url: str
    error_code: int
    timestamp: datetime
    message: str

@dataclass
class CrawlReport:
    source: str
    total_pages: int
    total_records: int
    total_errors: int
    duration_seconds: float
    start_time: datetime
    end_time: datetime
    errors: List[CrawlError] = field(default_factory=list)