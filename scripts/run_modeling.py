"""Train and persist the salary baseline model."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.salary_predictor import train_salary_model

if __name__ == "__main__":
    _, report, metadata = train_salary_model()
    print(report.to_string(index=False))
    print(f"Best model: {metadata['model_name']} | artifacts: reports/artifacts/")
