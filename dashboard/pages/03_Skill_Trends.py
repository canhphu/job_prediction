"""Skill demand and trend analytics page."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import plotly.express as px
import requests
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Initialize theme in session state before importing styles
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# Sidebar theme selector (synchronized globally)
is_dark = st.sidebar.toggle(
    "Chế độ tối (Dark Mode)",
    value=(st.session_state.theme == "dark"),
    key="skills_theme_toggle"
)
st.session_state.theme = "dark" if is_dark else "light"

from dashboard.components.filters import apply_sidebar_filters
from dashboard.components.styles import apply_custom_css, style_plotly_chart
from dashboard.services.data_loader import aggregate_timeline, explode_skills, load_jobs, require_data, timeline_axis_label, timeline_column

# Set page config
st.set_page_config(page_title="Skill Trends - IT Salary Hub", layout="wide")

# Apply custom styles
apply_custom_css()

st.title("Xu Hướng Kỹ Năng & Công Nghệ")
st.write("Khảo sát nhu cầu về các kỹ năng, ngôn ngữ lập trình, framework và công nghệ trong ngành IT:")


def main() -> None:
    df = load_jobs()
    if not require_data(df):
        return

    filtered = apply_sidebar_filters(df, key_prefix="skills")
    if filtered.empty:
        st.warning("No records match the selected filters.")
        st.stop()

    skills_df = explode_skills(filtered)
    if skills_df.empty:
        st.warning("No skill data available for the selected filters.")
        st.stop()

    # Top Skills (horizontal bar chart - Blue)
    top_skills = skills_df["skill"].value_counts().head(25).reset_index()
    top_skills.columns = ["skill", "jobs"]
    fig = px.bar(top_skills, x="jobs", y="skill", orientation="h", title="Top 25 Kỹ năng tuyển dụng nhiều nhất (Skill Demand)")
    style_plotly_chart(fig, "bar", theme=st.session_state.theme)
    # Force Top Skills to Blue
    fig.update_traces(marker_color="#2563eb", marker_line_color="#1d4ed8")
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=560, xaxis_title="Số lượng công việc yêu cầu")
    st.plotly_chart(fig, use_container_width=True)

    # Skill Comparison over Time
    st.write("---")
    st.subheader("So Sánh Xu Hướng Kỹ Năng Theo Thời Gian")
    st.write("Chọn các kỹ năng/công nghệ bạn muốn so sánh nhu cầu tuyển dụng qua các tuần/tháng:")
    
    selected = st.multiselect(
        "Lựa chọn các kỹ năng cần so sánh:",
        sorted(skills_df["skill"].unique()),
        default=top_skills["skill"].head(5).tolist(),
    )

    timeline_label = st.selectbox(
        "Tần suất hiển thị xu hướng kỹ năng",
        ["Weekly", "Monthly"],
        index=0,
        key="skills_timeline_mode",
    )
    timeline_mode = timeline_label.lower()

    if selected:
        trend = aggregate_timeline(skills_df[skills_df["skill"].isin(selected)], timeline_mode, group_cols=["skill"])
        if not trend.empty:
            time_col = timeline_column(timeline_mode)
            # Use high-contrast color sequence for lines (Set1/Dark2 equivalent or custom)
            fig = px.line(
                trend,
                x=time_col,
                y="jobs",
                color="skill",
                markers=True,
                title=f"Xu hướng tuyển dụng kỹ năng ({timeline_label})",
                category_orders={time_col: trend[time_col].drop_duplicates().tolist()},
                color_discrete_sequence=px.colors.qualitative.Dark24
            )
            style_plotly_chart(fig, "line", theme=st.session_state.theme)
            fig.update_layout(xaxis_title=timeline_axis_label(timeline_mode), yaxis_title="Số lượng công việc")
            st.plotly_chart(fig, use_container_width=True)

    # Forecast Section
    st.write("---")
    st.subheader("Dự báo xu hướng kỹ năng (Next 1–3 months)")
    st.write("Nhu cầu tuyển dụng kỹ năng IT dự báo dựa trên chuỗi thời gian (Time-series Forecasting):")
    
    try:
        api_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        forecast = requests.get(f"{api_url}/v1/analytics/trends", timeout=3).json().get("forecast", [])
        if forecast:
            forecast_df = pd.DataFrame(forecast)
            
            hdr_map = {
                "skill": "Kỹ năng",
                "current_volume": "Nhu cầu hiện tại",
                "forecasted_volume": "Dự báo (1-3 tháng)",
                "trend_direction": "Xu hướng dịch chuyển",
                "confidence_score": "Độ tin cậy"
            }
            forecast_df = forecast_df.rename(columns=hdr_map)
            st.dataframe(forecast_df, use_container_width=True, hide_index=True)
            st.caption("Dự báo chuỗi thời gian có sai số và chỉ mang tính tham khảo đối với biến động của thị trường.")
        else:
            st.info("Hiện tại chưa có tệp dữ liệu dự báo được tải sẵn.")
    except Exception:
        # Fallback explanation card adapting to light/dark
        card_border = "rgba(0, 0, 0, 0.05)" if st.session_state.theme == "light" else "rgba(255, 255, 255, 0.05)"
        card_bg = "rgba(255, 255, 255, 0.5)" if st.session_state.theme == "light" else "#111827"
        text_col = "#475569" if st.session_state.theme == "light" else "#94a3b8"
        title_col = "#0f172a" if st.session_state.theme == "light" else "#cbd5e1"
        st.markdown(
            f"""
            <div style="background-color: {card_bg}; border: 1px solid {card_border}; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
                <h5 style="color: {title_col}; margin-top:0; font-weight:600;">Dữ liệu dự báo chưa khả dụng</h5>
                <p style="color: {text_col}; font-size: 0.875rem; margin-bottom:0; line-height:1.5;">
                    Chức năng dự báo yêu cầu phân tích nâng cao. Bạn có thể xây dựng file phân tích bằng cách khởi chạy: 
                    <code>python scripts/run_analytics.py</code> sau đó khởi chạy API backend để nạp dữ liệu.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Role-Skill Heatmap (Adapting colorscale to light/dark)
    st.write("---")
    st.subheader("Bản Đồ Nhiệt Vai Trò - Kỹ Năng (Role-Skill Heatmap)")
    st.write("Trực quan hóa sự liên kết giữa các vị trí công việc IT và các kỹ năng công nghệ tương ứng:")
    
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
            title="Mật độ phân bổ Kỹ năng theo từng Vị trí công việc",
        )
        style_plotly_chart(fig, "heatmap", theme=st.session_state.theme)
        # Adapt color scale for light / dark mode
        colorscale = "Plasma" if st.session_state.theme == "light" else "Viridis"
        fig.update_traces(colorscale=colorscale)
        fig.update_layout(height=620, xaxis_title="Kỹ năng", yaxis_title="Vị trí công việc")
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
