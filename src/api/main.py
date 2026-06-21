"""FastAPI endpoints for the local hiring analytics application."""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from src.analytics.trends import load_analytics
from src.models.salary_predictor import load_model, predict_salary

app = FastAPI(title="Vietnam IT Hiring Analytics API", version="1.0.0")


class SalaryRequest(BaseModel):
    title: str = Field(min_length=2, examples=["Python Backend Developer"])
    location: str = Field(min_length=2, examples=["Ho Chi Minh City"])
    experience: str | float | int = Field(examples=["3 years"])
    job_level: str = Field(min_length=1, examples=["Mid"])
    description: str = Field(min_length=3, examples=["Python, FastAPI, PostgreSQL, Docker, AWS"])


def _artifact_error(exc: FileNotFoundError):
    raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/health")
def health():
    status = {"model_ready": False, "analytics_ready": False}
    try:
        _, metadata = load_model()
        status.update(model_ready=True, model_name=metadata["model_name"], trained_at=metadata["trained_at"])
    except FileNotFoundError:
        pass
    try:
        summary, _, _ = load_analytics()
        status.update(analytics_ready=True, data_range=summary.get("date_range", []))
    except FileNotFoundError:
        pass
    return status


@app.post("/v1/predict-salary")
def salary_prediction(payload: SalaryRequest):
    try:
        return predict_salary(**payload.model_dump())
    except FileNotFoundError as exc:
        _artifact_error(exc)


@app.get("/v1/analytics/summary")
def analytics_summary():
    try:
        summary, _, _ = load_analytics()
        try:
            _, metadata = load_model()
            summary["model"] = metadata
        except FileNotFoundError:
            summary["model"] = None
        return summary
    except FileNotFoundError as exc:
        _artifact_error(exc)


@app.get("/v1/analytics/skills")
def analytics_skills(limit: int = Query(default=10, ge=1, le=62)):
    try:
        summary, _, _ = load_analytics()
        return {"skills": summary["top_skills"][:limit]}
    except FileNotFoundError as exc:
        _artifact_error(exc)


@app.get("/v1/analytics/trends")
def analytics_trends(skill: str | None = None):
    try:
        _, history, forecast = load_analytics()
        if skill:
            history = history[history["skill"].str.lower() == skill.lower()]
            forecast = forecast[forecast["skill"].str.lower() == skill.lower()]
            if history.empty and forecast.empty:
                raise HTTPException(status_code=404, detail=f"Không tìm thấy skill: {skill}")
        return {"history": history.to_dict(orient="records"), "forecast": forecast.to_dict(orient="records")}
    except FileNotFoundError as exc:
        _artifact_error(exc)
