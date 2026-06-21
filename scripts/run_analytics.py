"""Generate dashboard-ready skill trend artifacts."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.trends import build_analytics

if __name__ == "__main__":
    summary, _, forecast = build_analytics()
    print(f"Analytics built for {summary['total_jobs']} jobs.")
    print(f"Forecast rows: {len(forecast)} | artifacts: reports/artifacts/")
