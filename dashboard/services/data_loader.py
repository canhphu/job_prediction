"""Data loading and preparation helpers for the Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "jobs_cleaned_full.csv"
TIMELINE_COLUMNS = {
    "monthly": "posted_month",
    "weekly": "posted_week",
}


def _empty_jobs_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "job_title",
            "company_name",
            "location",
            "posted_date",
            "salary_min",
            "salary_max",
            "salary_currency",
            "job_type",
            "job_level",
            "experience_required",
            "skills",
            "source",
            "salary_missing",
            "salary_avg",
            "salary_range",
            "experience_bucket",
            "skill_count",
            "posted_month",
            "posted_week",
        ]
    )


def _prepare_jobs(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ["job_title", "company_name", "location", "job_type", "job_level", "skills", "source"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    if "posted_date" not in df.columns:
        df["posted_date"] = pd.NaT
    df["posted_date"] = pd.to_datetime(df["posted_date"], errors="coerce")

    for col in ["salary_min", "salary_max", "salary_avg", "experience_required", "skill_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = pd.NA

    salary_min = pd.to_numeric(df.get("salary_min", pd.Series(dtype="float")), errors="coerce")
    salary_max = pd.to_numeric(df.get("salary_max", pd.Series(dtype="float")), errors="coerce")
    salary_avg = pd.to_numeric(df.get("salary_avg", pd.Series(dtype="float")), errors="coerce")
    estimated_avg = pd.concat([salary_min, salary_max], axis=1).mean(axis=1, skipna=True)
    df["salary_avg"] = salary_avg.fillna(estimated_avg)

    if "salary_missing" not in df.columns:
        df["salary_missing"] = df[["salary_min", "salary_max", "salary_avg"]].isna().all(axis=1)

    if "salary_range" not in df.columns:
        df["salary_range"] = pd.cut(
            df["salary_avg"],
            bins=[0, 10_000_000, 15_000_000, 20_000_000, 30_000_000, 50_000_000, float("inf")],
            labels=["<10M", "10-15M", "15-20M", "20-30M", "30-50M", ">50M"],
        ).astype("object")

    if "experience_bucket" not in df.columns:
        df["experience_bucket"] = pd.cut(
            df["experience_required"],
            bins=[-0.1, 1, 3, 5, 10, float("inf")],
            labels=["0-1", "1-3", "3-5", "5-10", "10+"],
        ).astype("object")

    df["posted_month"] = df["posted_date"].dt.to_period("M").astype(str).replace("NaT", "")
    df["posted_week"] = df["posted_date"].dt.strftime("%G-W%V").fillna("")

    return df


def timeline_column(mode: str) -> str:
    return TIMELINE_COLUMNS.get(mode, "posted_month")


def timeline_axis_label(mode: str) -> str:
    return "Week" if mode == "weekly" else "Month"


def aggregate_timeline(
    df: pd.DataFrame,
    mode: str = "monthly",
    group_cols: list[str] | tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Aggregate a dataframe by month or week for trend charts."""
    if df.empty or "posted_date" not in df.columns:
        return pd.DataFrame(columns=[timeline_column(mode), "jobs"])

    time_col = timeline_column(mode)
    cols = [time_col]
    if group_cols:
        cols.extend([col for col in group_cols if col in df.columns and col != time_col])

    data = df.dropna(subset=["posted_date"]).copy()
    if data.empty:
        return pd.DataFrame(columns=cols + ["jobs"])

    aggregated = (
        data.groupby(cols, as_index=False)
        .size()
        .rename(columns={"size": "jobs"})
        .sort_values(cols)
    )
    return aggregated


@st.cache_data(show_spinner="Loading job data...")
def load_jobs() -> pd.DataFrame:
    """Load the cleaned job table for dashboard analytics."""
    path = PROCESSED_PATH
    if not path.exists():
        return _empty_jobs_frame()

    df = pd.read_csv(path)
    return _prepare_jobs(df)


def require_data(df: pd.DataFrame) -> bool:
    """Render a clear error when the data files are missing."""
    if not df.empty:
        return True

    st.error("No job data found. Expected data/processed/jobs_cleaned_full.csv.")
    st.info("Run `python scripts/run_etl.py` if the cleaned file has not been generated yet, then reload the dashboard.")
    return False


def explode_skills(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per job-skill pair."""
    if df.empty or "skills" not in df.columns:
        return pd.DataFrame(columns=["job_title", "posted_date", "posted_month", "posted_week", "skill"])

    rows = []
    base_cols = [c for c in ["job_title", "location", "source", "posted_date", "posted_month", "posted_week"] if c in df.columns]
    for record in df[base_cols + ["skills"]].to_dict("records"):
        skills = [s.strip() for s in str(record.get("skills", "")).split(",") if s.strip()]
        for skill in skills:
            item = {col: record.get(col) for col in base_cols}
            item["skill"] = skill
            rows.append(item)
    return pd.DataFrame(rows)


def format_vnd(value: float | int | None) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{value / 1_000_000:,.1f}M VND"
