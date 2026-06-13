"""Model integration point for the salary predictor page.

The dashboard intentionally does not train or own the model. When a model
artifact or API is available, wire it behind ``predict_salary`` without
changing the Streamlit page.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


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
    """Placeholder contract for future model integration."""
    return PredictionResult(
        is_available=False,
        message="Salary model is not integrated yet. This page is ready for the model handoff.",
    )


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
