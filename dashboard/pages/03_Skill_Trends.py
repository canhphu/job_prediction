"""Skill demand and trend analytics page."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.filters import apply_sidebar_filters
from dashboard.services.data_loader import aggregate_timeline, explode_skills, load_jobs, require_data, timeline_axis_label, timeline_column


st.set_page_config(page_title="Skill Trends", layout="wide")
st.title("Skill Trends")

df = load_jobs()
if require_data(df):
    filtered = apply_sidebar_filters(df, key_prefix="skills")
    if filtered.empty:
        st.warning("No records match the selected filters.")
        st.stop()

    skills_df = explode_skills(filtered)
    if skills_df.empty:
        st.warning("No skill data available for the selected filters.")
        st.stop()

    top_skills = skills_df["skill"].value_counts().head(25).reset_index()
    top_skills.columns = ["skill", "jobs"]
    fig = px.bar(top_skills, x="jobs", y="skill", orientation="h", title="Top Skills")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=720)
    st.plotly_chart(fig, use_container_width=True)

    selected = st.multiselect(
        "Compare skills over time",
        sorted(skills_df["skill"].unique()),
        default=top_skills["skill"].head(5).tolist(),
    )

    timeline_label = st.selectbox(
        "Trend granularity",
        ["Weekly", "Monthly"],
        index=0,
        key="skills_timeline_mode",
    )
    timeline_mode = timeline_label.lower()

    if selected:
        trend = aggregate_timeline(skills_df[skills_df["skill"].isin(selected)], timeline_mode, group_cols=["skill"])
        if not trend.empty:
            time_col = timeline_column(timeline_mode)
            fig = px.line(
                trend,
                x=time_col,
                y="jobs",
                color="skill",
                markers=True,
                title=f"{timeline_label} Skill Demand Trend",
                category_orders={time_col: trend[time_col].drop_duplicates().tolist()},
            )
            fig.update_layout(xaxis_title=timeline_axis_label(timeline_mode), yaxis_title="Jobs")
            st.plotly_chart(fig, use_container_width=True)

    top_roles = filtered["job_title"].value_counts().head(12).index
    top_skill_names = top_skills["skill"].head(12).tolist()
    heatmap_source = explode_skills(filtered[filtered["job_title"].isin(top_roles)])
    heatmap_source = heatmap_source[heatmap_source["skill"].isin(top_skill_names)]
    heatmap = (
        heatmap_source.groupby(["job_title", "skill"], as_index=False)
        .size()
        .rename(columns={"size": "jobs"})
    )
    if not heatmap.empty:
        fig = px.density_heatmap(
            heatmap,
            x="skill",
            y="job_title",
            z="jobs",
            histfunc="sum",
            title="Role-Skill Heatmap",
        )
        fig.update_layout(height=620)
        st.plotly_chart(fig, use_container_width=True)
