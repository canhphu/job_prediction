"""Skill demand summaries and transparent three-month baseline forecasts."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ARTIFACTS_DIR, DATA_PROCESSED
from src.features.skill_extractor import MODEL_SKILLS, SKILL_COLUMN_MAP, add_skill_features


def build_analytics(input_path: Path = DATA_PROCESSED / "jobs_cleaned_full.csv", artifact_dir: Path = ARTIFACTS_DIR, top_n: int = 10) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Build dashboard-ready summary, skill history and forecast artifacts."""
    data = pd.read_csv(input_path)
    data["posted_date"] = pd.to_datetime(data.get("posted_date"), errors="coerce")
    data = add_skill_features(data)
    counts = {skill: int(data[column].sum()) for skill, column in SKILL_COLUMN_MAP.items()}
    top_skills = [skill for skill, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:top_n]]
    valid_dates = data["posted_date"].dropna()
    months = pd.period_range(valid_dates.min().to_period("M"), valid_dates.max().to_period("M"), freq="M").astype(str) if not valid_dates.empty else pd.Index([])
    data["posted_month"] = data["posted_date"].dt.to_period("M").astype(str).replace("NaT", np.nan)
    history_rows, forecast_rows = [], []
    for skill in top_skills:
        column = SKILL_COLUMN_MAP[skill]
        monthly = data.dropna(subset=["posted_month"]).groupby("posted_month")[column].sum().reindex(months, fill_value=0).astype(float)
        for month, count in monthly.items():
            history_rows.append({"skill": skill, "posted_month": month, "job_count": int(count), "rolling_average_3m": float(monthly.rolling(3, min_periods=1).mean().loc[month])})
        current = float(monthly.iloc[-1]) if len(monthly) else 0.0
        previous = float(monthly.iloc[-2]) if len(monthly) > 1 else 0.0
        growth = (current - previous) / previous if previous else 0.0
        if len(monthly) >= 3:
            slope, intercept = np.polyfit(np.arange(len(monthly)), monthly.values, 1)
            future = [max(0.0, float(slope * (len(monthly) + offset) + intercept)) for offset in range(3)]
        else:
            future = [float(monthly.tail(3).mean()) if len(monthly) else 0.0] * 3
        forecast_rows.append({"skill": skill, "current_month_count": current, "forecast_next_1_month": future[0], "forecast_next_2_month": future[1], "forecast_next_3_month": future[2], "growth_rate": growth, "trend_label": "Hot" if growth > .10 else "Declining" if growth < -.10 else "Stable", "history_months": len(monthly), "data_quality_warning": "Cần tối thiểu 3 tháng dữ liệu để forecast đáng tin cậy." if len(monthly) < 3 else "Baseline tuyến tính; diễn giải thận trọng."})
    history = pd.DataFrame(history_rows)
    forecast = pd.DataFrame(forecast_rows)
    summary = {
        "total_jobs": int(len(data)), "salary_coverage": round(float(data[["salary_min", "salary_max"]].notna().all(axis=1).mean()), 4),
        "skills_coverage": round(float(data["num_skills"].gt(0).mean()), 4), "date_range": [str(valid_dates.min().date()), str(valid_dates.max().date())] if not valid_dates.empty else [],
        "source_counts": {str(key): int(value) for key, value in data["source"].value_counts().items()}, "top_skills": [{"skill": skill, "job_count": counts[skill]} for skill in top_skills],
    }
    artifact_dir.mkdir(parents=True, exist_ok=True)
    history.to_csv(artifact_dir / "skill_month_history.csv", index=False)
    forecast.to_csv(artifact_dir / "skill_trend_forecast.csv", index=False)
    (artifact_dir / "analytics_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary, history, forecast


def load_analytics(artifact_dir: Path = ARTIFACTS_DIR) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    required = [artifact_dir / "analytics_summary.json", artifact_dir / "skill_month_history.csv", artifact_dir / "skill_trend_forecast.csv"]
    if any(not path.exists() for path in required):
        raise FileNotFoundError("Chưa có analytics artifact. Hãy chạy: python scripts/run_analytics.py")
    return json.loads(required[0].read_text(encoding="utf-8")), pd.read_csv(required[1]), pd.read_csv(required[2])
