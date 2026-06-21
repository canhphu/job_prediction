"""Metric components for dashboard pages."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.services.data_loader import format_vnd


def render_summary_metrics(df: pd.DataFrame) -> None:
    salary = pd.to_numeric(df.get("salary_avg"), errors="coerce")
    total_jobs = len(df)
    companies = df["company_name"].replace("", pd.NA).nunique() if "company_name" in df.columns else 0
    salary_coverage = salary.notna().mean() * 100 if total_jobs else 0
    median_salary = salary.median()

    cols = st.columns(4)
    cols[0].metric("Jobs", f"{total_jobs:,}")
    cols[1].metric("Companies", f"{companies:,}")
    cols[2].metric("Salary coverage", f"{salary_coverage:.1f}%")
    cols[3].metric("Median salary", format_vnd(median_salary))
