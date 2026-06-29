"""Main Streamlit entry point for the IT job market dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Initialize theme in session state before importing styles
if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# Sidebar theme switcher (must be defined early to react to changes)
is_dark = st.sidebar.toggle(
    "Chế độ tối (Dark Mode)",
    value=(st.session_state.theme == "dark"),
    key="global_theme_toggle"
)
st.session_state.theme = "dark" if is_dark else "light"


from dashboard.components.styles import apply_custom_css
from dashboard.services.data_loader import load_jobs, require_data, format_vnd
from dashboard.services.model_adapter import predict_salary, market_benchmark

# Set page config
st.set_page_config(
    page_title="Vietnam IT Salary Hub & Predictor",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom styling theme dynamically
apply_custom_css()


def main() -> None:
    df = load_jobs()
    if not require_data(df):
        return

    # Calculate metrics
    salary = pd.to_numeric(df.get("salary_avg"), errors="coerce")
    total_jobs = len(df)
    total_companies = df["company_name"].replace("", pd.NA).nunique() if "company_name" in df.columns else 0
    salary_coverage = salary.notna().mean() * 100 if total_jobs else 0
    median_salary = salary.median()
    median_salary_vnd = format_vnd(median_salary)

    # Render simulated tech status indicator at the top
    st.markdown(
        """
        <div class="system-status-indicator">
            <span class="status-dot"></span>
            <span>SYS_STATUS: ACTIVE</span>
            <span>|</span>
            <span>ML_MODEL: XGBOOST</span>
            <span>|</span>
            <span>LOAD_RATIO: 100%</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Render technology landing banner
    st.markdown(
        """
        <div class="tech-banner">
            <h1>Vietnam IT Salary Hub & Predictor</h1>
            <p>Hệ thống dự đoán lương và phân tích thị trường tuyển dụng công nghệ thông tin tại Việt Nam.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render metric cards (Using glass-card)
    st.markdown(
        f"""
        <div class="metric-container">
            <div class="glass-card">
                <div class="card-title">Tổng số công việc</div>
                <div class="card-value">{total_jobs:,}</div>
                <div class="card-subtitle">Tin tuyển dụng thu thập</div>
            </div>
            <div class="glass-card">
                <div class="card-title">Số công ty</div>
                <div class="card-value">{total_companies:,}</div>
                <div class="card-subtitle">Đơn vị tuyển dụng active</div>
            </div>
            <div class="glass-card">
                <div class="card-title">Độ phủ lương</div>
                <div class="card-value">{salary_coverage:.1f}%</div>
                <div class="card-subtitle">Có thông tin mức lương</div>
            </div>
            <div class="glass-card">
                <div class="card-title">Mức lương trung vị</div>
                <div class="card-value">{median_salary_vnd}</div>
                <div class="card-subtitle">Toàn thị trường IT</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Salary Predictor section
    st.subheader("Dự đoán Lương IT")
    st.write("Nhập thông tin hồ sơ công việc dưới đây để ước lượng mức lương thị trường dựa trên mô hình Machine Learning thực tế:")

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
            job_title = st.selectbox("Vị trí tuyển dụng (Job Category)", roles)
            job_level = st.selectbox("Cấp bậc (Job Level)", levels)
            experience = st.number_input("Số năm kinh nghiệm", min_value=0.0, max_value=30.0, value=2.0, step=0.5)
        with col2:
            location = st.selectbox("Địa điểm làm việc", locations)
            selected_skills = st.multiselect("Kỹ năng yêu cầu (Skills)", skills)

        submitted = st.form_submit_button("Ước Tính Mức Lương")

    if submitted:
        payload = {
            "job_title": job_title,
            "job_level": job_level,
            "experience_required": experience,
            "location": location,
            "skills": selected_skills,
        }

        # Fetch predictions and benchmarks
        result = predict_salary(payload)
        benchmark = market_benchmark(df, payload)

        pred_col, bench_col = st.columns(2)
        with pred_col:
            if result.is_available:
                val_vnd = format_vnd(result.prediction)
                lower_vnd = format_vnd(result.lower_bound)
                upper_vnd = format_vnd(result.upper_bound)
                
                # Render simulated Job Offer Card instead of simple metrics
                st.markdown(
                    f"""
                    <div class="job-offer-container">
                        <div class="job-offer-watermark">OFFER</div>
                        <div class="job-offer-header">
                            <div class="job-offer-title">Thư mời nhận việc</div>
                            <div class="job-offer-company">Ref: IT-SALARY-AI</div>
                        </div>
                        <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.25rem;">Đề xuất thu nhập ước tính cho vị trí của bạn:</div>
                        <div class="job-offer-salary">{val_vnd}</div>
                        <div class="job-offer-details">
                            <div><strong>Vị trí:</strong> {job_title}</div>
                            <div><strong>Cấp bậc:</strong> {job_level}</div>
                            <div><strong>Kinh nghiệm:</strong> {experience} năm</div>
                            <div><strong>Địa điểm:</strong> {location}</div>
                        </div>
                        <div class="job-offer-benefits">
                            <strong>Chỉ dẫn thị trường:</strong><br/>
                            - Khoảng lương dao động: {lower_vnd} - {upper_vnd}.<br/>
                            - Hệ thống dự đoán: {result.model_version} ({result.message}).
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.error(result.message)

        with bench_col:
            if benchmark["count"]:
                bench_val = format_vnd(benchmark["median"])
                p25_val = format_vnd(benchmark["p25"])
                p75_val = format_vnd(benchmark["p75"])
                st.markdown(
                    f"""
                    <div class="benchmark-card">
                        <div class="bench-label">THỰC TẾ THỊ TRƯỜNG (BENCHMARK)</div>
                        <div class="bench-value">{bench_val}</div>
                        <div class="pred-range">Khoảng IQR: {p25_val} - {p75_val}</div>
                        <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 0.5rem;">
                            Dựa trên mẫu gồm {benchmark['count']:,} tin tuyển dụng trùng khớp
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    """
                    <div class="benchmark-card">
                        <div class="bench-label">THỰC TẾ THỊ TRƯỜNG (BENCHMARK)</div>
                        <div style="font-size: 1.25rem; color: #f87171; font-weight: 700; margin: 1rem 0;">Không tìm thấy benchmark</div>
                        <div class="pred-range">Chưa có đủ mẫu tương tự trong dữ liệu</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # Dynamic Salary Range Visualizer
        if result.is_available and result.prediction:
            valid_salaries = salary.dropna()
            if len(valid_salaries) >= 10:
                s_min_market = float(valid_salaries.quantile(0.05))
                s_max_market = float(valid_salaries.quantile(0.95))
            else:
                s_min_market = 8_000_000.0
                s_max_market = 80_000_000.0

            if s_max_market == s_min_market:
                s_max_market += 10_000_000.0

            # Calculate position percentage
            pred_salary = float(result.prediction)
            pct = (pred_salary - s_min_market) / (s_max_market - s_min_market) * 100
            pct = max(4.0, min(96.0, pct))
            
            st.markdown(
                f"""
                <div class="salary-visualizer-container">
                    <div class="salary-visualizer-title">Phân khúc lương so với thị trường tuyển dụng</div>
                    <div class="salary-visualizer-track">
                        <div class="salary-visualizer-pointer" style="left: {pct}%;">
                            <div class="salary-visualizer-current-label">{format_vnd(pred_salary)}</div>
                        </div>
                    </div>
                    <div class="salary-visualizer-labels">
                        <span class="salary-visualizer-min">Phổ thông: {format_vnd(s_min_market)}</span>
                        <span class="salary-visualizer-max">Cao cấp: {format_vnd(s_max_market)}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Quick Navigation Cards (No Icons)
    st.write("---")
    st.subheader("Phân Tích Chuyên Sâu")
    st.write("Khám phá dữ liệu tuyển dụng và lương ngành IT qua các chuyên mục phân tích chi tiết:")
    
    st.markdown(
        """
        <div class="nav-container">
            <a href="./Overview" target="_self" class="nav-card">
                <div class="nav-title">Tổng Quan Thị Trường</div>
                <div class="nav-desc">Phân tích phân bố việc làm theo địa điểm, cấp bậc và theo dõi xu hướng tin tuyển dụng theo thời gian tuyển dụng.</div>
            </a>
            <a href="./Market_Analytics" target="_self" class="nav-card">
                <div class="nav-title">Phân Tích Lương IT</div>
                <div class="nav-desc">Xem chi tiết mức lương theo chức danh công việc, cấp bậc tuyển dụng và các công ty tuyển dụng hàng đầu.</div>
            </a>
            <a href="./Skill_Trends" target="_self" class="nav-card">
                <div class="nav-title">Xu Hướng Kỹ Năng</div>
                <div class="nav-desc">Khám phá các kỹ năng hot nhất, bản đồ nhiệt Vai trò - Kỹ năng và dự báo nhu cầu công nghệ trong tương lai.</div>
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
