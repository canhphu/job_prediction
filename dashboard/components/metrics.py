"""Metric components for dashboard pages."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.services.data_loader import format_vnd


def render_summary_metrics(df: pd.DataFrame) -> None:
    """Render summary metrics using beautiful HTML card containers."""
    salary = pd.to_numeric(df.get("salary_avg"), errors="coerce")
    total_jobs = len(df)
    companies = df["company_name"].replace("", pd.NA).nunique() if "company_name" in df.columns else 0
    salary_coverage = salary.notna().mean() * 100 if total_jobs else 0
    median_salary = salary.median()
    median_salary_vnd = format_vnd(median_salary)

    st.markdown(
        f"""
        <div class="metric-container">
            <div class="glass-card">
                <div class="card-title">Tổng số công việc</div>
                <div class="card-value">{total_jobs:,}</div>
                <div class="card-subtitle">Khớp bộ lọc hiện tại</div>
            </div>
            <div class="glass-card">
                <div class="card-title">Số công ty</div>
                <div class="card-value">{companies:,}</div>
                <div class="card-subtitle">Active trong bộ lọc</div>
            </div>
            <div class="glass-card">
                <div class="card-title">Độ phủ lương</div>
                <div class="card-value">{salary_coverage:.1f}%</div>
                <div class="card-subtitle">Có thông tin mức lương</div>
            </div>
            <div class="glass-card">
                <div class="card-title">Mức lương trung vị</div>
                <div class="card-value">{median_salary_vnd}</div>
                <div class="card-subtitle">Trong tập dữ liệu lọc</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
