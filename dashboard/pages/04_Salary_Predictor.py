"""Placeholder salary predictor page prepared for model integration."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.services.data_loader import format_vnd, load_jobs, require_data
from dashboard.services.model_adapter import market_benchmark, predict_salary


st.set_page_config(page_title="Salary Predictor", layout="wide")
st.title("Salary Predictor")
st.caption("The UI is ready for model integration. Current output includes a market benchmark only.")

df = load_jobs()
if require_data(df):
    def options(column: str, fallback: str) -> list[str]:
        values = sorted([v for v in df[column].dropna().unique() if str(v).strip()])
        return values or [fallback]

    roles = options("job_title", "Unknown")
    locations = options("location", "Unknown")
    levels = options("job_level", "Unknown")
    skills = sorted(
        {
            skill.strip()
            for values in df["skills"].fillna("").astype(str)
            for skill in values.split(",")
            if skill.strip()
        }
    )

    with st.form("salary_prediction_form"):
        col1, col2 = st.columns(2)
        with col1:
            job_title = st.selectbox("Job category", roles)
            job_level = st.selectbox("Job level", levels)
            experience = st.number_input("Experience required", min_value=0.0, max_value=30.0, value=2.0, step=0.5)
        with col2:
            location = st.selectbox("Location", locations)
            selected_skills = st.multiselect("Skills", skills)

        submitted = st.form_submit_button("Estimate salary")

    if submitted:
        payload = {
            "job_title": job_title,
            "job_level": job_level,
            "experience_required": experience,
            "location": location,
            "skills": selected_skills,
        }

        result = predict_salary(payload)
        benchmark = market_benchmark(df, payload)

        pred_col, bench_col = st.columns(2)
        with pred_col:
            st.subheader("Model Prediction")
            if result.is_available:
                st.metric("Predicted salary", format_vnd(result.prediction))
                st.caption(f"Model version: {result.model_version}")
                if result.lower_bound is not None and result.upper_bound is not None:
                    st.write(f"Range: {format_vnd(result.lower_bound)} - {format_vnd(result.upper_bound)}")
            else:
                st.info(result.message)

        with bench_col:
            st.subheader("Market Benchmark")
            if benchmark["count"]:
                st.metric("Median salary", format_vnd(benchmark["median"]))
                st.write(f"Sample size: {benchmark['count']:,} matching records")
                st.write(f"IQR: {format_vnd(benchmark['p25'])} - {format_vnd(benchmark['p75'])}")
            else:
                st.warning("No salary benchmark found for this exact selection.")

        with st.expander("Integration payload"):
            st.json(payload)
