"""Main Streamlit entry point for the IT job market dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components.filters import apply_sidebar_filters
from dashboard.components.metrics import render_summary_metrics
from dashboard.services.data_loader import load_jobs, require_data


st.set_page_config(
    page_title="IT Job Market Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    st.title("IT Job Market Dashboard")

if __name__ == "__main__":
    main()
