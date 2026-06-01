"""Feature Engineering"""

import os
from datetime import datetime
from typing import List, Optional

import numpy as np
import pandas as pd

from src.config import DATA_FEATURES
from src.utils.logger import get_logger

logger = get_logger(__name__)

TOP_SKILLS = [
    "AI", "SQL", "Java", "API", "Python", "Excel", "Agile", "REST",
    "Security", "CI/CD", "AWS", "Linux", "Docker", "Scrum", "ERP",
    "DevOps", "Git", "React", "CRM", "JavaScript",
]

CATEGORY_MAP = {
    "UI/UX Designer": "cat_UIUX",
    "Fullstack/Software Engineer": "cat_Fullstack",
    "AI/ML Engineer": "cat_AIML",
    "Other": "cat_Other",
    "Sales/Presales": "cat_Sales",
    "System/Network Admin": "cat_SysAdmin",
    "Business Analyst": "cat_BA",
    "QA/Tester": "cat_QA",
    "Backend Developer": "cat_Backend",
    "Project Manager": "cat_ProjectMgr",
    "IT Manager": "cat_ITMgr",
    "DevOps/Infra Engineer": "cat_DevOps",
    "Mobile Developer": "cat_Mobile",
    "Security Engineer": "cat_Security",
    "Frontend Developer": "cat_Frontend",
    "ERP/CRM Specialist": "cat_ERP",
    "Product Manager/Owner": "cat_ProductMgr",
    "Data Analyst": "cat_DataAnalyst",
    "IT Support": "cat_ITSupport",
    "Game Developer": "cat_Game",
    "Data Engineer": "cat_DataEngineer",
    "Consultant": "cat_Consultant",
    "Embedded Engineer": "cat_Embedded",
    "Cloud Engineer": "cat_Cloud",
    "Solution Architect": "cat_Architect",
    "Database Administrator": "cat_DBA",
    "Blockchain Developer": "cat_Blockchain",
}


class FeatureEngineer:
    """Create ML-ready features from cleaned job data."""

    def engineer_features(self, df: pd.DataFrame,
                          output_filename: str = "jobs_featured_full.csv") -> pd.DataFrame:
        logger.info("Feature engineering start: %d records", len(df))

        df = self._create_salary_avg(df)
        df = self._create_salary_range(df)
        df = self._create_experience_bucket(df)
        df = self._create_skill_count(df)
        df = self._encode_skills(df, TOP_SKILLS)
        df = self._create_domain_flags(df)
        df = self._create_time_features(df)
        df = self._encode_job_level(df)
        df = self._encode_location(df)
        df = self._encode_job_category(df)

        os.makedirs(DATA_FEATURES, exist_ok=True)
        output_path = DATA_FEATURES / output_filename
        df.to_csv(output_path, index=False, encoding="utf-8")
        logger.info("Saved %d records (%d cols) to %s", len(df), len(df.columns), output_path)
        return df

    def _create_salary_avg(self, df):
        df = df.copy()
        s_min = pd.to_numeric(df.get("salary_min"), errors="coerce")
        s_max = pd.to_numeric(df.get("salary_max"), errors="coerce")
        both = s_min.notna() & s_max.notna()
        df["salary_avg"] = np.where(both, (s_min + s_max) / 2, np.nan)
        return df

    def _create_salary_range(self, df):
        df = df.copy()
        def classify(val):
            if pd.isna(val): return None
            if val < 10_000_000: return "<10M"
            elif val < 15_000_000: return "10-15M"
            elif val < 20_000_000: return "15-20M"
            elif val < 30_000_000: return "20-30M"
            elif val < 50_000_000: return "30-50M"
            else: return ">50M"
        df["salary_range"] = df["salary_avg"].apply(classify)
        return df

    def _create_experience_bucket(self, df):
        df = df.copy()
        exp = pd.to_numeric(df.get("experience_required"), errors="coerce")
        def classify(v):
            if pd.isna(v): return None
            if v <= 1: return "0-1"
            elif v <= 3: return "1-3"
            elif v <= 5: return "3-5"
            elif v <= 10: return "5-10"
            else: return "10+"
        df["experience_bucket"] = exp.apply(classify)
        return df

    def _create_skill_count(self, df):
        df = df.copy()
        def count(val):
            if not val or (isinstance(val, float) and pd.isna(val)):
                return 0
            return len([s for s in str(val).split(",") if s.strip()])
        df["skill_count"] = df["skills"].apply(count)
        return df

    def _encode_skills(self, df, skill_list):
        df = df.copy()
        def parse(val):
            if not val or (isinstance(val, float) and pd.isna(val)):
                return set()
            return set(s.strip().lower() for s in str(val).split(",") if s.strip())
        parsed = df["skills"].apply(parse)
        for skill in skill_list:
            col = f"skill_{skill.replace('/', '_').replace(' ', '_')}"
            sl = skill.lower()
            df[col] = parsed.apply(lambda s, k=sl: 1 if k in s else 0)
        return df

    def _create_domain_flags(self, df):
        df = df.copy()
        def has_any(val, keywords):
            if not val or (isinstance(val, float) and pd.isna(val)):
                return 0
            v = str(val).lower()
            return 1 if any(k.lower() in v for k in keywords) else 0
        df["has_cloud"] = df["skills"].apply(lambda s: has_any(s, ["AWS", "Azure", "GCP"]))
        df["has_ai_ml"] = df["skills"].apply(lambda s: has_any(s, ["AI", "Machine Learning", "TensorFlow", "PyTorch", "NLP"]))
        df["has_devops"] = df["skills"].apply(lambda s: has_any(s, ["Docker", "Kubernetes", "CI/CD", "DevOps"]))
        df["has_data"] = df["skills"].apply(lambda s: has_any(s, ["SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis"]))
        return df

    def _create_time_features(self, df):
        df = df.copy()
        df["posted_month"] = df["posted_date"].apply(
            lambda d: d[:7] if d and len(str(d)) >= 7 else None
        )
        def to_week(d):
            if not d or len(str(d)) < 10: return None
            try:
                dt = datetime.strptime(str(d), "%Y-%m-%d")
                iso = dt.isocalendar()
                return f"{iso[0]}-W{iso[1]:02d}"
            except ValueError:
                return None
        df["posted_week"] = df["posted_date"].apply(to_week)
        return df

    def _encode_job_level(self, df):
        df = df.copy()
        for level in ["Intern", "Junior", "Mid", "Senior", "Manager+"]:
            col = f"job_level_{level.replace('+', 'Plus')}"
            df[col] = (df["job_level"] == level).astype(int)
        return df

    def _encode_location(self, df):
        df = df.copy()
        df["location_Hanoi"] = (df["location"] == "Hanoi").astype(int)
        df["location_HCM"] = (df["location"] == "Ho Chi Minh City").astype(int)
        df["location_DaNang"] = (df["location"] == "Da Nang").astype(int)
        df["location_Other"] = (df["location"] == "Other").astype(int)
        return df

    def _encode_job_category(self, df):
        df = df.copy()
        for category, col_name in CATEGORY_MAP.items():
            df[col_name] = (df["job_title"] == category).astype(int)
        return df