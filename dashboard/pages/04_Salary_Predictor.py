"""Side-by-side Salary Comparison & Explorer page."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
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
    key="compare_theme_toggle"
)
st.session_state.theme = "dark" if is_dark else "light"

from dashboard.components.styles import apply_custom_css, style_plotly_chart
from dashboard.services.data_loader import format_vnd, load_jobs, require_data
from dashboard.services.model_adapter import market_benchmark, predict_salary

# Set page config
st.set_page_config(page_title="Salary Comparison - IT Salary Hub", layout="wide")

# Apply custom styles
apply_custom_css()

st.title("So Sánh Lương Song Song")
st.write("So sánh mức lương dự kiến giữa hai cấu hình công việc khác nhau để đưa ra quyết định định hướng nghề nghiệp:")


def main() -> None:
    df = load_jobs()
    if not require_data(df):
        return

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

    # Use a form for input comparison
    with st.form("salary_comparison_form"):
        prof_a_col, prof_b_col = st.columns(2)
        
        with prof_a_col:
            st.markdown(
                """
                <div style="background-color: rgba(99, 102, 241, 0.15); padding: 0.75rem; border-radius: 8px; border: 1px solid rgba(99, 102, 241, 0.3); text-align: center; font-weight: bold; color: #818cf8; margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.05em;">
                    Hồ sơ công việc A
                </div>
                """,
                unsafe_allow_html=True
            )
            job_title_a = st.selectbox("Vị trí (Job Category) - A", roles, key="title_a")
            job_level_a = st.selectbox("Cấp bậc (Level) - A", levels, key="level_a")
            experience_a = st.number_input("Kinh nghiệm (năm) - A", min_value=0.0, max_value=30.0, value=2.0, step=0.5, key="exp_a")
            location_a = st.selectbox("Địa điểm - A", locations, key="loc_a")
            selected_skills_a = st.multiselect("Kỹ năng (Skills) - A", skills, key="skills_a")

        with prof_b_col:
            st.markdown(
                """
                <div style="background-color: rgba(16, 185, 129, 0.15); padding: 0.75rem; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.3); text-align: center; font-weight: bold; color: #34d399; margin-bottom: 1rem; text-transform: uppercase; letter-spacing: 0.05em;">
                    Hồ sơ công việc B
                </div>
                """,
                unsafe_allow_html=True
            )
            default_role_index = min(len(roles) - 1, 1)
            job_title_b = st.selectbox("Vị trí (Job Category) - B", roles, index=default_role_index, key="title_b")
            job_level_b = st.selectbox("Cấp bậc (Level) - B", levels, key="level_b")
            experience_b = st.number_input("Kinh nghiệm (năm) - B", min_value=0.0, max_value=30.0, value=2.0, step=0.5, key="exp_b")
            location_b = st.selectbox("Địa điểm - B", locations, key="loc_b")
            selected_skills_b = st.multiselect("Kỹ năng (Skills) - B", skills, key="skills_b")

        submitted = st.form_submit_button("Bắt Đầu So Sánh")

    if submitted:
        payload_a = {
            "job_title": job_title_a,
            "job_level": job_level_a,
            "experience_required": experience_a,
            "location": location_a,
            "skills": selected_skills_a,
        }
        payload_b = {
            "job_title": job_title_b,
            "job_level": job_level_b,
            "experience_required": experience_b,
            "location": location_b,
            "skills": selected_skills_b,
        }

        # Predict
        res_a = predict_salary(payload_a)
        res_b = predict_salary(payload_b)
        
        bench_a = market_benchmark(df, payload_a)
        bench_b = market_benchmark(df, payload_b)

        if not res_a.is_available or not res_b.is_available:
            st.error("Lỗi: Không thể thực hiện dự đoán lương cho một trong hai hồ sơ.")
            return

        # Render outputs in columns
        col_out_a, col_out_b = st.columns(2)
        
        with col_out_a:
            val_a_vnd = format_vnd(res_a.prediction)
            lower_a_vnd = format_vnd(res_a.lower_bound)
            upper_a_vnd = format_vnd(res_a.upper_bound)
            bench_a_vnd = format_vnd(bench_a["median"]) if bench_a["median"] else "N/A"
            st.markdown(
                f"""
                <div class="prediction-result-card">
                    <h5 style="margin: 0; color: #818cf8; font-weight: 700; text-transform: uppercase;">Dự báo hồ sơ A</h5>
                    <div class="pred-value">{val_a_vnd}</div>
                    <div class="pred-range">Khoảng ước lượng: {lower_a_vnd} - {upper_a_vnd}</div>
                    <div style="font-size: 0.875rem; color: #cbd5e1; margin-top: 1rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.75rem;">
                        Trung vị thực tế thị trường: <strong>{bench_a_vnd}</strong> ({bench_a['count']} mẫu)
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_out_b:
            val_b_vnd = format_vnd(res_b.prediction)
            lower_b_vnd = format_vnd(res_b.lower_bound)
            upper_b_vnd = format_vnd(res_b.upper_bound)
            bench_b_vnd = format_vnd(bench_b["median"]) if bench_b["median"] else "N/A"
            st.markdown(
                f"""
                <div class="prediction-result-card" style="background: linear-gradient(145deg, rgba(6, 78, 59, 0.5) 0%, rgba(17, 24, 39, 0.8) 100%); border-color: rgba(5, 150, 105, 0.3);">
                    <h5 style="margin: 0; color: #34d399; font-weight: 700; text-transform: uppercase;">Dự báo hồ sơ B</h5>
                    <div class="pred-value" style="color: #34d399; text-shadow: 0 0 12px rgba(52, 211, 153, 0.3);">{val_b_vnd}</div>
                    <div class="pred-range">Khoảng ước lượng: {lower_b_vnd} - {upper_b_vnd}</div>
                    <div style="font-size: 0.875rem; color: #cbd5e1; margin-top: 1rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.75rem;">
                        Trung vị thực tế thị trường: <strong>{bench_b_vnd}</strong> ({bench_b['count']} mẫu)
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Comparative Analytics & Difference Comment (No Icons)
        st.write("---")
        st.subheader("Phân Tích So Sánh Trực Quan")
        
        pred_a = res_a.prediction
        pred_b = res_b.prediction
        
        diff = pred_b - pred_a
        diff_pct = (diff / pred_a) * 100 if pred_a else 0
        
        if diff > 0:
            comparison_text = f"Hồ sơ B có mức lương dự đoán cao hơn Hồ sơ A khoảng <strong>{format_vnd(diff)}</strong> (tăng <strong>{diff_pct:.1f}%</strong>)."
            style_color = "#10b981"
        elif diff < 0:
            comparison_text = f"Hồ sơ A có mức lương dự đoán cao hơn Hồ sơ B khoảng <strong>{format_vnd(-diff)}</strong> (tăng <strong>{-diff_pct:.1f}%</strong>)."
            style_color = "#3b82f6"
        else:
            comparison_text = "Hai hồ sơ có mức lương dự kiến tương đương nhau."
            style_color = "#94a3b8"

        card_bg = "rgba(255, 255, 255, 0.5)" if st.session_state.theme == "light" else "#111827"
        st.markdown(
            f"""
            <div style="background-color: {card_bg}; border-left: 5px solid {style_color}; padding: 1.25rem 1.5rem; border-radius: 6px; margin-bottom: 2rem;">
                <span style="font-size: 1.1rem; color: inherit;">{comparison_text}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Plotly chart comparison
        compare_data = pd.DataFrame([
            {"Profile": "Hồ sơ A", "Loại": "Mức lương dự đoán", "Lương (VND)": pred_a},
            {"Profile": "Hồ sơ A", "Loại": "Benchmark thực tế", "Lương (VND)": bench_a["median"] or 0},
            {"Profile": "Hồ sơ B", "Loại": "Mức lương dự đoán", "Lương (VND)": pred_b},
            {"Profile": "Hồ sơ B", "Loại": "Benchmark thực tế", "Lương (VND)": bench_b["median"] or 0},
        ])

        fig = px.bar(
            compare_data,
            x="Profile",
            y="Lương (VND)",
            color="Loại",
            barmode="group",
            title="Biểu đồ so sánh mức lương dự đoán vs Benchmark thị trường",
            color_discrete_map={
                "Mức lương dự đoán": "#6366f1",
                "Benchmark thực tế": "#10b981"
            }
        )
        style_plotly_chart(fig, "bar", theme=st.session_state.theme)
        fig.update_layout(height=450, xaxis_title="")
        fig.update_yaxes(tickformat=",.0s")
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
