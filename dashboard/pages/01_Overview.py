"""Combined Overview page: summary metrics and charts."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Initialize theme in session state before importing styling helpers
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# Sidebar theme selector (synchronized globally)
is_dark = st.sidebar.toggle(
    "Chế độ tối (Dark Mode)",
    value=(st.session_state.theme == "dark"),
    key="overview_theme_toggle"
)
st.session_state.theme = "dark" if is_dark else "light"

from dashboard.components.filters import apply_sidebar_filters
from dashboard.components.metrics import render_summary_metrics
from dashboard.components.styles import apply_custom_css, style_plotly_chart
from dashboard.services.data_loader import aggregate_timeline, load_jobs, require_data, timeline_axis_label, timeline_column

# Set page config
st.set_page_config(page_title="Overview - IT Job Market", layout="wide")

# Apply custom styling theme dynamically
apply_custom_css()

st.title("Tổng Quan Thị Trường IT")
st.markdown(
    """
    <div class="page-subheader-highlight">
        Phân tích tổng thể nhu cầu tuyển dụng công nghệ thông tin dựa trên dữ liệu thu thập
    </div>
    """,
    unsafe_allow_html=True
)


def main() -> None:
    df = load_jobs()
    if not require_data(df):
        return

    filtered = apply_sidebar_filters(df, key_prefix="overview")
    if filtered.empty:
        st.warning("No records match the selected filters.")
        st.stop()

    # Summary metrics cards
    render_summary_metrics(filtered)

    # Location (Blue) and Level (Amber/Yellow) in 2 columns to distinguish colors
    col1, col2 = st.columns(2)
    with col1:
        location_counts = filtered["location"].value_counts().reset_index()
        location_counts.columns = ["location", "jobs"]
        fig = px.bar(location_counts, x="location", y="jobs", title="Số lượng công việc theo địa điểm (Location)")
        style_plotly_chart(fig, "bar", theme=st.session_state.theme)
        # Force Location chart to Blue
        fig.update_traces(marker_color="#2563eb", marker_line_color="#1d4ed8")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        level_counts = filtered["job_level"].replace("", "Unknown").value_counts().reset_index()
        level_counts.columns = ["job_level", "jobs"]
        fig = px.bar(level_counts, x="job_level", y="jobs", title="Số lượng công việc theo cấp bậc (Level)")
        style_plotly_chart(fig, "bar", theme=st.session_state.theme)
        # Force Level chart to Amber/Orange (distinguish from Location Blue)
        fig.update_traces(marker_color="#f59e0b", marker_line_color="#d97706")
        st.plotly_chart(fig, use_container_width=True)

    # Top job categories (combined view - Purple)
    role_counts = filtered["job_title"].value_counts().head(15).reset_index()
    role_counts.columns = ["job_title", "jobs"]
    fig = px.bar(role_counts, x="jobs", y="job_title", orientation="h", title="Top 15 vị trí tuyển dụng nhiều nhất (Job Categories)")
    style_plotly_chart(fig, "bar", theme=st.session_state.theme)
    # Force Top Categories to Indigo/Purple
    fig.update_traces(marker_color="#8b5cf6", marker_line_color="#6d28d9")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=560)
    st.plotly_chart(fig, use_container_width=True)

    # Jobs by source + overall top breakdown in 2 columns
    left, right = st.columns(2)
    with left:
        source_counts = filtered["source"].value_counts().reset_index()
        source_counts.columns = ["source", "jobs"]
        fig = px.pie(source_counts, names="source", values="jobs", title="Tỷ lệ nguồn tuyển dụng (Sources)", hole=0.45)
        style_plotly_chart(fig, "pie", theme=st.session_state.theme)
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        timeline_label = st.selectbox(
            "Tần suất hiển thị xu hướng",
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
                title=f"Xu hướng đăng tuyển dụng theo {timeline_axis_label(timeline_mode)}",
                category_orders={time_col: trend[time_col].drop_duplicates().tolist()},
            )
            style_plotly_chart(fig, "line", theme=st.session_state.theme)
            # Use specific emerald/green for line trend to avoid color clash
            fig.update_traces(line=dict(color="#10b981", width=3), marker=dict(color="#047857", size=6))
            fig.update_layout(xaxis_title=timeline_axis_label(timeline_mode), yaxis_title="Số lượng công việc")
            st.plotly_chart(fig, use_container_width=True)

    # Timeline trend by source
    st.write("---")
    st.subheader("Phân Tích Xu Hướng Nguồn Tuyển Dụng")
    source_timeline_label = st.selectbox(
        "Tần suất hiển thị xu hướng nguồn tuyển",
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
            title=f"Xu hướng tin tuyển dụng theo từng nguồn ({source_timeline_label})",
            category_orders={time_col: source_trend[time_col].drop_duplicates().tolist()},
        )
        style_plotly_chart(fig, "line", theme=st.session_state.theme)
        fig.update_layout(xaxis_title=timeline_axis_label(source_timeline_mode), yaxis_title="Số lượng công việc")
        st.plotly_chart(fig, use_container_width=True)

    # Recent records
    st.write("---")
    st.subheader("Danh sách công việc mới nhất")
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
    recent_jobs = filtered.sort_values("posted_date", ascending=False, na_position="last")[table_cols].head(100)
    
    header_map = {
        "posted_date": "Ngày đăng",
        "job_title": "Vị trí tuyển dụng",
        "company_name": "Tên công ty",
        "location": "Địa điểm",
        "job_level": "Cấp bậc",
        "salary_avg": "Lương trung bình",
        "skills": "Kỹ năng",
        "source": "Nguồn"
    }
    
    recent_jobs_display = recent_jobs.rename(columns=header_map)
    if "Lương trung bình" in recent_jobs_display.columns:
        from dashboard.services.data_loader import format_vnd
        recent_jobs_display["Lương trung bình"] = recent_jobs_display["Lương trung bình"].apply(format_vnd)
        
    st.dataframe(
        recent_jobs_display,
        use_container_width=True,
        hide_index=True,
    )


if __name__ == "__main__":
    main()
