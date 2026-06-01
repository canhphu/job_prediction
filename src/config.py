"""Centralized configuration"""

from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

#  Directory paths
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_FEATURES = PROJECT_ROOT / "data" / "features"
LOGS_DIR = PROJECT_ROOT / "logs"

# Crawler settings
CRAWL_DELAY = 2.0
MAX_RETRIES = 3

# Valid categorial values
VALID_JOB_TYPES = ["Full-time", "Part-time", "Internship", "Contract", "Remote"]
VALID_JOB_LEVELS = ["Intern", "Junior", "Mid", "Senior", "Manager+"]