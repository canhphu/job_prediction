"""CSS and Chart styling helpers for Streamlit pages with Light/Dark support."""

from __future__ import annotations

from pathlib import Path
import streamlit as st


def apply_custom_css() -> None:
    """Read the theme-specific CSS file and inject it into the Streamlit page."""
    # Retrieve current theme from session state, default to dark
    current_theme = st.session_state.get("theme", "dark")
    filename = "style_light.css" if current_theme == "light" else "style_dark.css"
    
    css_path = Path(__file__).resolve().parents[1] / "assets" / filename
    if css_path.exists():
        try:
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
        except Exception:
            pass


def style_plotly_chart(fig, chart_type: str = "bar", theme: str | None = None) -> None:
    """Apply technology theme colors and layout configuration to Plotly charts based on theme."""
    if theme is None:
        theme = st.session_state.get("theme", "dark")

    # Set theme specific styling tokens
    if theme == "light":
        font_color = "#334155"  # Slate 700
        grid_color = "#e2e8f0"  # Slate 200
        title_color = "#0f172a" # Slate 900
        zero_line_color = "#cbd5e1"
    else:
        font_color = "#cbd5e1"  # Slate 300
        grid_color = "#1e293b"  # Slate 800
        title_color = "#ffffff"
        zero_line_color = "#334155"

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=font_color),
        title=dict(font=dict(color=title_color, size=16, weight="bold")),
        margin=dict(l=40, r=40, t=50, b=40),
        legend=dict(font=dict(color=font_color), bgcolor="rgba(0,0,0,0)")
    )
    
    if chart_type in ["bar", "line", "box", "heatmap"]:
        fig.update_xaxes(
            showgrid=False, 
            color=font_color, 
            title_font=dict(size=12, color=font_color),
            tickfont=dict(color=font_color),
            zeroline=True,
            zerolinecolor=zero_line_color
        )
        fig.update_yaxes(
            gridcolor=grid_color, 
            color=font_color, 
            title_font=dict(size=12, color=font_color),
            tickfont=dict(color=font_color),
            zeroline=True,
            zerolinecolor=zero_line_color
        )

    # Decorate with high-contrast palette if colors are not already customized
    if theme == "light":
        if chart_type == "bar":
            # Check if color is default before overriding
            fig.update_traces(
                marker_line_color="#1d4ed8", 
                marker_line_width=1, 
                opacity=0.85
            )
        elif chart_type == "line":
            fig.update_traces(
                line=dict(width=3), 
                marker=dict(size=6, line=dict(color="#f8fafc", width=1))
            )
        elif chart_type == "pie":
            fig.update_traces(
                marker=dict(
                    colors=["#2563eb", "#10b981", "#8b5cf6", "#f59e0b", "#ec4899", "#06b6d4"],
                    line=dict(color="#ffffff", width=1.5)
                ),
                textinfo='percent+label'
            )
        elif chart_type == "box":
            fig.update_traces(
                marker_color="#4f46e5",
                line=dict(color="#3730a3", width=1.5)
            )
        elif chart_type == "heatmap":
            fig.update_traces(colorscale="Cividis")
    else:
        # Dark Theme Chart Styling Defaults
        if chart_type == "bar":
            fig.update_traces(
                marker_line_color="#1d4ed8", 
                marker_line_width=1, 
                opacity=0.9
            )
        elif chart_type == "line":
            fig.update_traces(
                line=dict(width=3), 
                marker=dict(size=6, line=dict(color="#080b11", width=1))
            )
        elif chart_type == "pie":
            fig.update_traces(
                marker=dict(
                    colors=["#3b82f6", "#4f46e5", "#10b981", "#8b5cf6", "#f59e0b", "#ec4899"],
                    line=dict(color="#111827", width=1)
                ),
                textinfo='percent+label'
            )
        elif chart_type == "box":
            fig.update_traces(
                marker_color="#6366f1",
                line=dict(color="#818cf8", width=1.5)
            )
        elif chart_type == "heatmap":
            fig.update_traces(colorscale="Viridis")
