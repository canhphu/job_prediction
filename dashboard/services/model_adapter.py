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
    """Call the local FastAPI predictor, fallback to offline local predictor if unavailable."""
    api_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    request = {
        "title": payload.get("job_title", ""),
        "location": payload.get("location", ""),
        "experience": payload.get("experience_required", 2.0),
        "job_level": payload.get("job_level", ""),
        "description": ", ".join(payload.get("skills", [])),
    }
    try:
        response = requests.post(f"{api_url}/v1/predict-salary", json=request, timeout=2)
        response.raise_for_status()
        data = response.json()
        return PredictionResult(
            is_available=True,
            message=data.get("disclaimer", "Mức lương ước tính dựa trên mô hình phân tích tuyển dụng IT Việt Nam."),
            prediction=data["predicted_salary_vnd"],
            lower_bound=data.get("estimated_salary_min"),
            upper_bound=data.get("estimated_salary_max"),
            currency="VND",
            model_version=data.get("model", "baseline")
        )
    except requests.RequestException:
        # Fallback to local offline prediction directly using the python model code
        try:
            from src.models.salary_predictor import predict_salary as local_predict
            res = local_predict(
                title=request["title"],
                location=request["location"],
                experience=request["experience"],
                job_level=request["job_level"],
                description=request["description"]
            )
            return PredictionResult(
                is_available=True,
                message=res.get("disclaimer", "Mức lương ước tính dựa trên mô hình cục bộ (Local Fallback)."),
                prediction=res["predicted_salary_vnd"],
                lower_bound=res.get("estimated_salary_min"),
                upper_bound=res.get("estimated_salary_max"),
                currency="VND",
                model_version=res.get("model", "local-offline")
            )
        except Exception as local_exc:
            return PredictionResult(
                is_available=False,
                message=f"Không thể kết nối API hoặc chạy mô hình cục bộ. Chi tiết: {local_exc}"
            )


def market_benchmark(df: pd.DataFrame, payload: dict[str, Any]) -> dict[str, float | int | None]:
    """Compute a simple data benchmark for the selected inputs."""
    if df.empty:
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

    if "salary_avg" in subset.columns:
        salary_source = subset["salary_avg"]
    elif {"salary_min", "salary_max"}.issubset(subset.columns):
        salary_source = subset[["salary_min", "salary_max"]].apply(pd.to_numeric, errors="coerce").mean(axis=1)
    else:
        return {"count": 0, "median": None, "p25": None, "p75": None}

    salary = pd.to_numeric(salary_source, errors="coerce").dropna()
    if salary.empty:
        return {"count": 0, "median": None, "p25": None, "p75": None}

    return {
        "count": int(len(salary)),
        "median": float(salary.median()),
        "p25": float(salary.quantile(0.25)),
        "p75": float(salary.quantile(0.75)),
    }
