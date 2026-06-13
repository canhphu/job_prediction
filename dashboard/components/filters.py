"""Reusable sidebar filters for dashboard pages."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def _sorted_options(series: pd.Series) -> list[str]:
    return sorted([str(v) for v in series.dropna().unique() if str(v).strip()])


def apply_sidebar_filters(df: pd.DataFrame, key_prefix: str = "global") -> pd.DataFrame:
    """Render standard filters and return a filtered dataframe."""
    if df.empty:
        return df

    st.sidebar.header("Filters")
    filtered = df.copy()

    if "posted_date" in filtered.columns and filtered["posted_date"].notna().any():
        min_date = filtered["posted_date"].min().date()
        max_date = filtered["posted_date"].max().date()
        date_range = st.sidebar.date_input(
            "Posted date",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key=f"{key_prefix}_date",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
            filtered = filtered[(filtered["posted_date"] >= start) & (filtered["posted_date"] <= end)]

    for column, label in [
        ("source", "Source"),
        ("location", "Location"),
        ("job_title", "Job category"),
        ("job_level", "Job level"),
        ("salary_range", "Salary range"),
    ]:
        if column in filtered.columns:
            options = _sorted_options(filtered[column])
            selected = st.sidebar.multiselect(label, options, key=f"{key_prefix}_{column}")
            if selected:
                filtered = filtered[filtered[column].isin(selected)]

    if "skills" in filtered.columns:
        skills = sorted(
            {
                skill.strip()
                for values in filtered["skills"].fillna("").astype(str)
                for skill in values.split(",")
                if skill.strip()
            }
        )
        selected_skills = st.sidebar.multiselect("Skills", skills, key=f"{key_prefix}_skills")
        if selected_skills:
            selected_lower = {skill.lower() for skill in selected_skills}
            filtered = filtered[
                filtered["skills"].fillna("").astype(str).apply(
                    lambda values: bool(
                        selected_lower
                        & {skill.strip().lower() for skill in values.split(",") if skill.strip()}
                    )
                )
            ]

    st.sidebar.caption(f"{len(filtered):,} of {len(df):,} records")
    return filtered
