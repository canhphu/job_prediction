"""Shared rule-based skill extraction for training, analytics and inference."""

import re
from typing import Iterable

import pandas as pd


MODEL_SKILLS = [
    "Python", "Java", "JavaScript", "TypeScript", "React", "Vue", "Angular",
    "Node.js", "Express", "SQL", "MySQL", "PostgreSQL", "MongoDB", "Redis",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Linux", "Git", "CI/CD",
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "Data Analysis",
    "Data Engineering", "Spark", "Hadoop", "Airflow", "Kafka", "Power BI", "Tableau",
    "Excel", "C++", "C#", "PHP", "Laravel", "Django", "Flask", "FastAPI",
    "Spring Boot", "Android", "iOS", "Flutter", "DevOps", "Security", "Testing", "QA",
    "TensorFlow", "PyTorch", "Terraform", "Jenkins", "GraphQL", "HTML", "CSS", "Go",
    "Ruby", "Scala", "R", "Selenium",
]

SKILL_SLUGS = {"C++": "c_plus_plus", "C#": "c_sharp"}
SKILL_COLUMN_MAP = {
    skill: "skill_" + SKILL_SLUGS.get(skill, re.sub(r"[^a-z0-9]+", "_", skill.lower()).strip("_"))
    for skill in MODEL_SKILLS
}


def clean_text(value) -> str:
    """Return a safe, whitespace-normalized text value."""
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _pattern(skill: str) -> re.Pattern:
    aliases = {
        "Node.js": r"\b(node\.?js|nodejs)\b",
        "Vue": r"\b(vue\.?js|vuejs|vue)\b",
        "CI/CD": r"\b(ci/cd|cicd)\b",
        "C#": r"c#|csharp",
        "C++": r"c\+\+|cpp",
    }
    if skill in aliases:
        return re.compile(aliases[skill], re.IGNORECASE)
    escaped = re.escape(skill).replace(r"\ ", r"\s*")
    return re.compile(r"(?<![\w+#.])" + escaped + r"(?![\w+#.])", re.IGNORECASE)


SKILL_PATTERNS = {skill: _pattern(skill) for skill in MODEL_SKILLS}


def extract_skills(text) -> list[str]:
    """Extract canonical model skills from a description or comma-separated skill list."""
    content = clean_text(text)
    return [skill for skill, pattern in SKILL_PATTERNS.items() if pattern.search(content)]


def combine_skills(*values) -> list[str]:
    """Extract unique skills from any number of text fields, preserving vocabulary order."""
    content = " ".join(clean_text(value) for value in values)
    return extract_skills(content)


def add_skill_features(df: pd.DataFrame, skills_column: str = "skills", description_column: str = "description") -> pd.DataFrame:
    """Add canonical extracted skills, count and unique multi-hot model feature columns."""
    result = df.copy()
    skills = result.get(skills_column, pd.Series("", index=result.index))
    descriptions = result.get(description_column, pd.Series("", index=result.index))
    result["skills_extracted"] = [combine_skills(skill, description) for skill, description in zip(skills, descriptions)]
    result["num_skills"] = result["skills_extracted"].str.len()
    for skill, column in SKILL_COLUMN_MAP.items():
        result[column] = result["skills_extracted"].apply(lambda found, item=skill: int(item in found))
    return result


def skill_columns() -> list[str]:
    return list(SKILL_COLUMN_MAP.values())
