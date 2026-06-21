import pandas as pd

from src.etl.cleaner import Cleaner


def test_cleaner_preserves_compact_description():
    raw = pd.DataFrame([{"job_title": "Python Developer", "company_name": "Example", "location": "Hanoi", "salary_min": "20000000", "salary_max": "30000000", "skills": "Python", "job_type": "full-time", "job_level": "junior", "experience_required": "2", "posted_date": "2026-06-01", "job_description": "  Build   APIs with Python. ", "source": "fixture"}])
    cleaned = Cleaner().clean(raw)
    assert cleaned.loc[0, "description"] == "Build APIs with Python."
    assert cleaned.loc[0, "experience_required"] == "2.0"
