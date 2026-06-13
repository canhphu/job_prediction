"""Salary and market analytics page."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.filters import apply_sidebar_filters
from dashboard.services.data_loader import format_vnd, load_jobs, require_data


st.set_page_config(page_title="Market Analytics", layout="wide")
st.title("Market Analytics")

df = load_jobs()
if require_data(df):
    filtered = apply_sidebar_filters(df, key_prefix="market")
    if filtered.empty:
        st.warning("No records match the selected filters.")
        st.stop()

    salary_df = filtered.dropna(subset=["salary_avg"]).copy()
    st.caption(f"{len(salary_df):,} records with usable salary from {len(filtered):,} filtered records.")

    if salary_df.empty:
        st.warning("No salary data available for the selected filters.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            top_roles = salary_df["job_title"].value_counts().head(12).index
            fig = px.box(
                salary_df[salary_df["job_title"].isin(top_roles)],
                x="salary_avg",
                y="job_title",
                orientation="h",
                title="Salary Distribution by Job Category",
            )
            fig.update_layout(xaxis_title="Salary VND", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            level_salary = (
                salary_df.assign(job_level=salary_df["job_level"].replace("", "Unknown"))
                .groupby("job_level", as_index=False)["salary_avg"]
                .median()
                .sort_values("salary_avg", ascending=False)
            )
            fig = px.bar(level_salary, x="job_level", y="salary_avg", title="Median Salary by Level")
            fig.update_layout(yaxis_title="Median salary VND", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

        location_salary = (
            salary_df.groupby("location", as_index=False)
            .agg(jobs=("salary_avg", "size"), median_salary=("salary_avg", "median"))
            .sort_values("median_salary", ascending=False)
        )
        fig = px.bar(
            location_salary,
            x="location",
            y="median_salary",
            text=location_salary["median_salary"].apply(format_vnd),
            hover_data=["jobs"],
            title="Median Salary by Location",
        )
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Companies and Records")
    company_counts = (
        filtered["company_name"].replace("", "Unknown").value_counts().head(20).reset_index()
    )
    company_counts.columns = ["company_name", "jobs"]
    fig = px.bar(company_counts, x="jobs", y="company_name", orientation="h", title="Top Companies by Posting Count")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
    st.plotly_chart(fig, use_container_width=True)

    table_cols = [
        "posted_date",
        "job_title",
        "company_name",
        "location",
        "job_level",
        "experience_bucket",
        "salary_avg",
        "salary_range",
        "skills",
        "source",
    ]
    table_cols = [col for col in table_cols if col in filtered.columns]
    csv = filtered[table_cols].to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered CSV", csv, "filtered_jobs.csv", "text/csv")
    st.dataframe(filtered[table_cols], use_container_width=True, hide_index=True)
