import pandas as pd

from src.analytics.trends import build_analytics
from src.features.skill_extractor import SKILL_COLUMN_MAP, add_skill_features


def test_skill_columns_are_unique_and_keep_c_variants():
    assert len(SKILL_COLUMN_MAP) == len(set(SKILL_COLUMN_MAP.values()))
    assert SKILL_COLUMN_MAP["C++"] == "skill_c_plus_plus"
    assert SKILL_COLUMN_MAP["C#"] == "skill_c_sharp"


def test_analytics_uses_display_skill_names(tmp_path):
    rows = []
    for month in ("2026-01-15", "2026-02-15", "2026-03-15"):
        rows.append({"job_title": "Backend Developer", "location": "Hanoi", "posted_date": month, "salary_min": 20_000_000, "salary_max": 30_000_000, "skills": "Python, SQL", "source": "fixture"})
    source = tmp_path / "jobs.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    _, history, forecast = build_analytics(source, tmp_path)
    assert "Python" in set(history["skill"])
    assert not any(skill.startswith("skill_") for skill in forecast["skill"])
    assert forecast["forecast_next_1_month"].notna().all()


def test_skill_extraction_creates_unique_columns():
    featured = add_skill_features(pd.DataFrame([{"skills": "C++, C#, Python", "description": ""}]))
    assert featured.loc[0, "skill_c_plus_plus"] == 1
    assert featured.loc[0, "skill_c_sharp"] == 1
