"""Combined Overview page: summary metrics and charts.

This page consolidates the charts previously shown in `app.py` and the
original `01_Overview.py` so there is a single Overview page under Pages.
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.filters import apply_sidebar_filters
from dashboard.components.metrics import render_summary_metrics
from dashboard.services.data_loader import aggregate_timeline, load_jobs, require_data, timeline_axis_label, timeline_column


st.set_page_config(page_title="Overview", layout="wide")
st.title("Overview")


def main() -> None:
    df = load_jobs()
    if not require_data(df):
        return

    filtered = apply_sidebar_filters(df, key_prefix="overview")
    if filtered.empty:
        st.warning("No records match the selected filters.")
        st.stop()

    render_summary_metrics(filtered)

    # Location and Level
    col1, col2 = st.columns(2)
    with col1:
        location_counts = filtered["location"].value_counts().reset_index()
        location_counts.columns = ["location", "jobs"]
        fig = px.bar(location_counts, x="location", y="jobs", title="Jobs by Location")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        level_counts = filtered["job_level"].replace("", "Unknown").value_counts().reset_index()
        level_counts.columns = ["job_level", "jobs"]
        fig = px.bar(level_counts, x="job_level", y="jobs", title="Jobs by Level")
        st.plotly_chart(fig, use_container_width=True)

    # Top job categories (combined view)
    role_counts = filtered["job_title"].value_counts().head(15).reset_index()
    role_counts.columns = ["job_title", "jobs"]
    fig = px.bar(role_counts, x="jobs", y="job_title", orientation="h", title="Top 15 Job Categories")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=560)
    st.plotly_chart(fig, use_container_width=True)

    # Jobs by source + overall top breakdown
    left, right = st.columns(2)
    with left:
        source_counts = filtered["source"].value_counts().reset_index()
        source_counts.columns = ["source", "jobs"]
        fig = px.pie(source_counts, names="source", values="jobs", title="Jobs by Source", hole=0.45)
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        timeline_label = st.selectbox(
            "Trend granularity",
            ["Weekly", "Monthly"],
            index=0,
            key="overview_total_timeline_mode",
        )
        timeline_mode = timeline_label.lower()
        trend = aggregate_timeline(filtered, timeline_mode)
        if not trend.empty:
            time_col = timeline_column(timeline_mode)
            fig = px.line(
                trend,
                x=time_col,
                y="jobs",
                markers=True,
                title=f"{timeline_label} Job Posting Trend",
                category_orders={time_col: trend[time_col].drop_duplicates().tolist()},
            )
            fig.update_layout(xaxis_title=timeline_axis_label(timeline_mode), yaxis_title="Jobs")
            st.plotly_chart(fig, use_container_width=True)

    # Timeline trend by source
    source_timeline_label = st.selectbox(
        "Source trend granularity",
        ["Weekly", "Monthly"],
        index=0,
        key="overview_source_timeline_mode",
    )
    source_timeline_mode = source_timeline_label.lower()
    source_trend = aggregate_timeline(filtered, source_timeline_mode, group_cols=["source"])
    if not source_trend.empty:
        time_col = timeline_column(source_timeline_mode)
        fig = px.line(
            source_trend,
            x=time_col,
            y="jobs",
            color="source",
            markers=True,
            title=f"{source_timeline_label} Trend by Source",
            category_orders={time_col: source_trend[time_col].drop_duplicates().tolist()},
        )
        fig.update_layout(xaxis_title=timeline_axis_label(source_timeline_mode), yaxis_title="Jobs")
        st.plotly_chart(fig, use_container_width=True)

    # Recent records
    st.subheader("Recent Records")
    table_cols = [
        "posted_date",
        "job_title",
        "company_name",
        "location",
        "job_level",
        "salary_avg",
        "skills",
        "source",
    ]
    table_cols = [col for col in table_cols if col in filtered.columns]
    st.dataframe(
        filtered.sort_values("posted_date", ascending=False, na_position="last")[table_cols].head(100),
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
