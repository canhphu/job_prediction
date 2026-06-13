param(
    [int]$Port = 8501
)

Set-Location (Resolve-Path "$PSScriptRoot\..")
python -m streamlit run dashboard/app.py --server.headless=true --server.port=$Port --browser.gatherUsageStats=false
