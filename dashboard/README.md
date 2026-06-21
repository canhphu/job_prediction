# Streamlit Dashboard

Dashboard for exploring Vietnam IT job market data. This scope only builds the
user interface and analytics pages. Salary model integration is isolated in
`dashboard/services/model_adapter.py` and can be wired later by the model team.

## Setup

Run from the project root:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Check dashboard dependencies:

```powershell
python -c "import streamlit, plotly, pandas, numpy; print('dashboard deps ok')"
```

## Data

The dashboard reads only the cleaned file:

`data/processed/jobs_cleaned_full.csv`

If the file is missing, run:

```powershell
python scripts/run_etl.py
```

## Run

```powershell
streamlit run dashboard/app.py
```

Or use the helper script:

```powershell
.\dashboard\run_streamlit.ps1 -Port 8501
```

Port `8501` is Streamlit's default port. If it is already in use, choose another
port, for example `.\dashboard\run_streamlit.ps1 -Port 8502`.

## Pages

- `Overview`: high-level counts, location, level, role and per-chart weekly/monthly trends.
- `Market Analytics`: salary distribution, median salary and downloadable table.
- `Skill Trends`: top skills, skill trend comparison and role-skill heatmap.
- `Salary Predictor`: form and model integration placeholder. Until a real
  model is available, it shows a market benchmark from matching historical rows.

## Page Statistics (Meaning of Tables and Charts)

Below is a concise explanation of the tables and statistical charts shown on each page. The sidebar filters (date range, source, location, job level, job title, skills) apply to all pages and affect the displayed numbers.

- **Overview**:
    - **Summary metrics**: aggregate counts such as total job postings, unique companies, and unique locations within the selected filters.
    - **Top Job Categories**: horizontal bar chart of the top job titles by number of postings (top 10).
    - **Jobs by Source**: pie chart showing proportion of postings from each source (TopCV, ITviec, LinkedIn, CareerViet, etc.).
    - **Job Posting Trend**: line chart of postings by month or week (`posted_month` / `posted_week`) with its own granularity dropdown.
    - **Jobs by Source trend**: line chart of postings by month or week grouped by source, also with its own granularity dropdown.
    - **Recent Records table**: latest postings with columns (posted_date, job_title, company_name, location, job_level, salary_avg, skills, source) when available.

- **Market Analytics**:
    - **Salary distribution**: histogram / violin or box plots of `salary_avg` for the filtered subset to visualise spread and outliers.
    - **Median / Aggregates**: median, 25th and 75th percentiles and count for the selected filters and groupings (by role, location, level).
    - **Salary range categories**: counts per bucket (e.g., `<10M`, `10-15M`, ... `>50M`).
    - **Downloadable table**: filtered rows with salary fields so users can export the data used to compute the charts.

- **Skill Trends**:
    - **Top Skills**: ranked list/table of most frequently mentioned skills (by count of job postings where the skill appears).
    - **Skill trend comparison**: time-series showing how selected skills change in frequency by month or week, with its own granularity dropdown.
    - **Role–Skill heatmap**: matrix showing frequency or proportion of a skill appearing in postings for each role (useful for identifying skill-role relationships).
    - **Exploded skills table**: (one row per job-skill) used to compute trends and heatmaps.

- **Salary Predictor**:
    - **Input form**: select `job_title`, `job_level`, `location`, `experience_required`, and `skills`.
    - **Market benchmark**: for the chosen inputs, the dashboard computes `count`, `median`, `p25`, and `p75` of historical `salary_avg` values from matching rows and displays them as a quick reference.
    - **Model prediction**: when a model is integrated, the page will show `prediction`, `lower_bound`, `upper_bound`, and `model_version`. Currently this remains a placeholder.

If you want these descriptions translated to Vietnamese or expanded with field-level definitions (e.g. how `salary_avg` is computed), tell me which parts to expand.

## Model Handoff Contract

Keep the Streamlit page unchanged and implement this function:

```python
def predict_salary(payload: dict) -> PredictionResult:
    ...
```

Expected payload:

```python
{
    "job_title": "Backend Developer",
    "job_level": "Senior",
    "experience_required": 3.0,
    "location": "Hanoi",
    "skills": ["Python", "SQL"]
}
```

Expected result fields:

```python
PredictionResult(
    is_available=True,
    message="ok",
    prediction=25000000,
    lower_bound=20000000,
    upper_bound=32000000,
    currency="VND",
    model_version="v1.0",
)
```
