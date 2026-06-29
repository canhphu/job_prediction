"""Salary and market analytics page."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
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
    key="market_theme_toggle"
)
st.session_state.theme = "dark" if is_dark else "light"

from dashboard.components.filters import apply_sidebar_filters
from dashboard.components.styles import apply_custom_css, style_plotly_chart
from dashboard.services.data_loader import format_vnd, load_jobs, require_data

# Set page config
st.set_page_config(page_title="Market Analytics - IT Salary Hub", layout="wide")

# Apply custom styles
apply_custom_css()

st.title("Phân Tích Lương & Thị Trường IT")
st.write("Khảo sát mức lương ngành công nghệ thông tin theo nhóm vai trò, cấp bậc tuyển dụng và địa điểm làm việc:")


def main() -> None:
    df = load_jobs()
    if not require_data(df):
        return

    filtered = apply_sidebar_filters(df, key_prefix="market")
    if filtered.empty:
        st.warning("No records match the selected filters.")
        st.stop()

    salary_df = filtered.dropna(subset=["salary_avg"]).copy()
    
    st.markdown(
        f"""
        <div style="background-color: rgba(30, 41, 59, 0.4); border-left: 4px solid #10b981; padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 1.5rem;">
            Phát hiện <strong>{len(salary_df):,}</strong> tin tuyển dụng có thông tin lương khả dụng trên tổng số <strong>{len(filtered):,}</strong> tin tuyển dụng sau bộ lọc.
        </div>
        """, 
        unsafe_allow_html=True
    )

    if salary_df.empty:
        st.warning("No salary data available for the selected filters.")
    else:
        # Salary distribution by job title (box plot) and salary by level (bar plot) in 2 columns
        col1, col2 = st.columns(2)
        with col1:
            top_roles = salary_df["job_title"].value_counts().head(12).index
            fig = px.box(
                salary_df[salary_df["job_title"].isin(top_roles)],
                x="salary_avg",
                y="job_title",
                orientation="h",
                title="Phân bố lương theo vai trò công việc (Distribution)",
            )
            style_plotly_chart(fig, "box", theme=st.session_state.theme)
            # Force Box plot to Indigo
            fig.update_traces(marker_color="#6366f1", line=dict(color="#4f46e5"))
            fig.update_layout(xaxis_title="Mức lương (VND)", yaxis_title="")
            fig.update_xaxes(tickformat=",.0s")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            level_salary = (
                salary_df.assign(job_level=salary_df["job_level"].replace("", "Unknown"))
                .groupby("job_level", as_index=False)["salary_avg"]
                .median()
                .sort_values("salary_avg", ascending=False)
            )
            fig = px.bar(level_salary, x="job_level", y="salary_avg", title="Mức lương trung vị theo cấp bậc (Median Salary)")
            style_plotly_chart(fig, "bar", theme=st.session_state.theme)
            # Force Level Bar chart to Emerald (distinguish from Box Indigo)
            fig.update_traces(marker_color="#10b981", marker_line_color="#047857")
            fig.update_layout(yaxis_title="Lương trung vị (VND)", xaxis_title="")
            fig.update_yaxes(tickformat=",.0s")
            st.plotly_chart(fig, use_container_width=True)

        # Salary by location (full-width bar plot - Purple)
        st.write("---")
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
            title="Mức lương trung vị theo địa điểm làm việc (Median Salary by Location)",
        )
        style_plotly_chart(fig, "bar", theme=st.session_state.theme)
        # Force Location Bar chart to Violet/Purple (distinguish from Level Emerald and Box Indigo)
        fig.update_traces(textposition="outside", marker_color="#8b5cf6", marker_line_color="#6d28d9")
        fig.update_layout(yaxis_title="Lương trung vị (VND)", xaxis_title="")
        fig.update_yaxes(tickformat=",.0s")
        st.plotly_chart(fig, use_container_width=True)

    # Top Companies by Posting Count
    st.write("---")
    left_c, right_c = st.columns([2, 1])
    
    with left_c:
        st.subheader("Các nhà tuyển dụng nổi bật")
        company_counts = (
            filtered["company_name"].replace("", "Unknown").value_counts().head(12).reset_index()
        )
        company_counts.columns = ["company_name", "jobs"]
        fig = px.bar(company_counts, x="jobs", y="company_name", orientation="h", title="Top Công ty có số lượng đăng tuyển nhiều nhất")
        style_plotly_chart(fig, "bar", theme=st.session_state.theme)
        # Force Top Companies to Sky Blue (distinguish from others)
        fig.update_traces(marker_color="#0ea5e9", marker_line_color="#0284c7")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=450, xaxis_title="Số lượng công việc")
        st.plotly_chart(fig, use_container_width=True)
        
    with right_c:
        st.subheader("Tải dữ liệu lọc")
        st.write("Bạn có thể tải xuống toàn bộ tập dữ liệu đã áp dụng bộ lọc hiện tại ở định dạng CSV để tự phân tích thêm:")
        
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
        
        st.download_button(
            label="Tải dữ liệu CSV",
            data=csv,
            file_name="vietnam_it_jobs_filtered.csv",
            mime="text/csv",
        )
        st.write(f"Kích thước tệp: {len(filtered):,} bản ghi tuyển dụng.")

    # Data Table View
    st.write("---")
    st.subheader("Bảng chi tiết dữ liệu sau lọc")
    
    header_map = {
        "posted_date": "Ngày đăng",
        "job_title": "Vị trí tuyển dụng",
        "company_name": "Tên công ty",
        "location": "Địa điểm",
        "job_level": "Cấp bậc",
        "experience_bucket": "Kinh nghiệm",
        "salary_avg": "Lương TB",
        "salary_range": "Khoảng lương",
        "skills": "Kỹ năng",
        "source": "Nguồn"
    }
    
    jobs_display = filtered[table_cols].rename(columns=header_map).copy()
    if "Lương TB" in jobs_display.columns:
        jobs_display["Lương TB"] = jobs_display["Lương TB"].apply(format_vnd)
        
    st.dataframe(jobs_display.head(200), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
