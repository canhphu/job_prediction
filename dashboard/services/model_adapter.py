"""Model integration point for the salary predictor page.

The dashboard intentionally does not train or own the model. When a model
artifact or API is available, wire it behind ``predict_salary`` without
changing the Streamlit page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import os

import pandas as pd
import requests


@dataclass
class PredictionResult:
    is_available: bool
    message: str
    prediction: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    currency: str = "VND"
    model_version: str = "not-integrated"


def predict_salary(payload: dict[str, Any]) -> PredictionResult:
    """Call the local FastAPI predictor without coupling Streamlit to model code."""
    api_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    request = {
        "title": payload.get("job_title", ""), "location": payload.get("location", ""),
        "experience": payload.get("experience_required", 0), "job_level": payload.get("job_level", ""),
        "description": ", ".join(payload.get("skills", [])),
    }
    try:
        response = requests.post(f"{api_url}/v1/predict-salary", json=request, timeout=10)
        response.raise_for_status()
        data = response.json()
        return PredictionResult(True, data.get("disclaimer", "Baseline estimate."), data["predicted_salary_vnd"], currency="VND", model_version=data.get("model", "baseline"))
    except requests.RequestException as exc:
        return PredictionResult(False, f"Salary API unavailable: {exc}. Run run_modeling.py, run_analytics.py, then uvicorn src.api.main:app --reload.")


def market_benchmark(df: pd.DataFrame, payload: dict[str, Any]) -> dict[str, float | int | None]:
    """Compute a simple data benchmark for the selected inputs."""
    if df.empty or "salary_avg" not in df.columns:
        return {"count": 0, "median": None, "p25": None, "p75": None}

    subset = df.copy()
    for column, key in [("job_title", "job_title"), ("location", "location"), ("job_level", "job_level")]:
        value = payload.get(key)
        if value and column in subset.columns:
            subset = subset[subset[column] == value]

    selected_skills = {skill.lower() for skill in payload.get("skills", [])}
    if selected_skills and "skills" in subset.columns:
        subset = subset[
            subset["skills"].fillna("").astype(str).apply(
                lambda values: bool(
                    selected_skills
                    & {skill.strip().lower() for skill in values.split(",") if skill.strip()}
                )
            )
        ]

    salary = pd.to_numeric(subset["salary_avg"], errors="coerce").dropna()
    if salary.empty:
        return {"count": 0, "median": None, "p25": None, "p75": None}

    return {
        "count": int(len(salary)),
        "median": float(salary.median()),
        "p25": float(salary.quantile(0.25)),
        "p75": float(salary.quantile(0.75)),
    }
