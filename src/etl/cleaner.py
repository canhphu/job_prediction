"""Data cleaning pipeline"""

import ast
import re
from typing import List, Optional, Tuple

import pandas as pd

from src.etl.categorizer import categorize_title
from src.etl.skill_whitelist import SKILL_ALIASES, VALID_SKILLS
from src.utils.logger import get_logger

logger = get_logger(__name__)

# --- Normalization mappings ---

LOCATION_NORMALIZE = {
    "hanoi": "Hanoi", "ha noi": "Hanoi", "hà nội": "Hanoi",
    "ho chi minh": "Ho Chi Minh City", "hcm": "Ho Chi Minh City",
    "ho chi minh city": "Ho Chi Minh City", "hồ chí minh": "Ho Chi Minh City",
    "da nang": "Da Nang", "đà nẵng": "Da Nang",
}

JOB_TYPE_NORMALIZE = {
    "full-time": "Full-time", "part-time": "Part-time",
    "internship": "Internship", "contract": "Contract",
    "remote": "Remote", "on-site": "Full-time",
    "hybrid": "Full-time", "temporary": "Contract",
    "freelance/contract": "Contract", "other": "Full-time",
}

JOB_LEVEL_NORMALIZE = {
    "intern": "Intern", "internship": "Intern", "fresher": "Intern",
    "fresh graduate": "Intern", "student / intern": "Intern",
    "junior": "Junior", "entry level": "Junior", "associate": "Junior",
    "staff": "Mid", "mid-senior level": "Mid", "not applicable": "Mid", "middle": "Mid",
    "senior": "Senior", "team lead": "Senior", "team lead / supervisor": "Senior",
    "manager": "Manager+", "manager / supervisor": "Manager+",
    "department head / deputy": "Manager+", "director": "Manager+",
    "executive": "Manager+", "vice director": "Manager+",
}

class Cleaner:
    """Clean raw job data into standardized format."""

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        original_count = len(df)
        logger.info("Cleaning pipeline start: %d records", original_count)

        # Drop unnecessary columns
        drop_cols = ["job_description", "benefits", "company_size", "deadline"]
        df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

        # Remove low-quality records
        df = df[df["job_titles"].notna() & (df["job_titles"].str.len() >= 3)]
        df = df[df["company_name"].notna() & df["company_name"].str.len() > 0]

        # Clean job title
        df["job_title"] = df["job_title"].apply(self._clean_title)

        # Normalize fields
        df["location"] = df["location"].apply(self._normalize_location)
        df["job_type"] = df["job_type"].apply(self._normalize_job_type)
        df["job_level"] = df["job_level"].apply(self._normalize_job_level)

        # Fix level/title mismatch
        df = self._fix_level_mismatch(df)

        # Clean salary
        df["salary_min"] = df["salary_min"].apply(self._clean_salary)
        df["salary_max"] = df["salary_max"].apply(self._clean_salary)
        df["salary_missing"] = (df["salary_min"].isna() & df["salary_max"].isna())
        df["salary_currency"] = df.apply(
            lambda r: "VND" if not r["salary_missing"] else "", axis=1
        )

        # Parse skills (whitelist only)
        df["skills"] = df["skills"].apply(self._parse_skills)

        # Clean experience
        df["experience_required"] = df["experience_required"].apply(self._clean_experience)

        # Categorize job_title → 27 groups
        df["job_title"] = df["job_title"].apply(categorize_title)

        # Dedup
        before = len(df)
        df = df.drop_duplicates(
            subset=["job_title", "company_name", "source"], keep="first"
        ).reset_index(drop=True)
        logger.info("Dedup: %d → %d (removed %d)", before, len(df), before - len(df))

        # Select output columns
        output_cols = [
            "job_title", "company_name", "location", "posted_date",
            "salary_min", "salary_max", "salary_currency",
            "job_type", "job_level", "experience_required", "skills",
            "source", "salary_missing",
        ]
        df = df[[c for c in output_cols if c in df.columns]]

        logger.info("Cleaning complete: %d → %d records", original_count, len(df))
        return df

    @staticmethod
    def _clean_title(title: str) -> str:
        if not title:
            return ""
        title = re.sub(r"^\[.*?\]\s*", "", title)
        title = re.sub(r"\(Mới\)\s*$", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\([A-Z0-9.]+\)\s*$", "", title)
        title = re.sub(r"\s*[-–]\s*(?:Khối|Phòng|Ban|Trung tâm|Division|Department).*$", "", title)
        return title.strip().strip("-–—").strip()

    @staticmethod
    def _normalize_location(loc) -> str:
        if not loc or pd.isna(loc):
            return "Other"
        loc_lower = str(loc).lower().strip()
        for key, city in LOCATION_NORMALIZE.items():
            if key in loc_lower:
                return city
        return "Other"

    @staticmethod
    def _normalize_job_type(jt) -> str:
        if not jt or pd.isna(jt):
            return "Full-time"
        first = str(jt).split(",")[0].strip().lower()
        return JOB_TYPE_NORMALIZE.get(first, "Full-time")

    @staticmethod
    def _normalize_job_level(jl) -> str:
        if not jl or pd.isna(jl):
            return ""
        return JOB_LEVEL_NORMALIZE.get(str(jl).lower().strip(), "")

    @staticmethod
    def _fix_level_mismatch(df: pd.DataFrame) -> pd.DataFrame:
        mask = (
            df["job_title"].str.contains("senior", case=False, na=False)
            & (df["job_level"] == "Mid")
        )
        df.loc[mask, "job_level"] = "Senior"
        fixed = mask.sum()
        if fixed:
            logger.info("Fixed %d level mismatches (title=Senior, level=Mid)", fixed)
        return df

    @staticmethod
    def _clean_salary(val) -> Optional[float]:
        if not val or pd.isna(val):
            return None
        try:
            v = float(val)
            if v < 1_000_000 or v > 200_000_000:
                return None
            return v
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _clean_experience(val) -> str:
        if not val or pd.isna(val):
            return ""
        try:
            return str(float(val))
        except (ValueError, TypeError):
            return ""

    @staticmethod
    def _parse_skills(skills_str) -> str:
        if not skills_str or pd.isna(skills_str):
            return ""
        if str(skills_str).strip() in ("", "[]", "['']", "None"):
            return ""

        skills_str = str(skills_str)
        skills_list = []

        if skills_str.startswith("["):
            try:
                parsed = ast.literal_eval(skills_str)
                if isinstance(parsed, list):
                    skills_list = [str(s).strip() for s in parsed if s]
            except (ValueError, SyntaxError):
                inner = skills_str.strip("[]")
                skills_list = [s.strip().strip("'\"") for s in inner.split(",") if s.strip()]
        else:
            skills_list = [s.strip() for s in skills_str.split(",") if s.strip()]

        cleaned = []
        seen = set()
        for skill in skills_list:
            if not skill or len(skill) < 2:
                continue
            skill_lower = skill.lower().strip()
            if skill_lower in SKILL_ALIASES:
                skill = SKILL_ALIASES[skill_lower]
                skill_lower = skill.lower()
            if skill_lower not in VALID_SKILLS:
                continue
            if skill_lower not in seen:
                seen.add(skill_lower)
                cleaned.append(skill)

        return ", ".join(cleaned)