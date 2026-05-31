# IT Hiring Trends Forecasting (Vietnam)

This repository supports a data science course project on analyzing and forecasting IT hiring trends in Vietnam.

## Structure

- data/
  - incoming/   # Drop-in area for existing CSVs from scraping
  - raw/        # Immutable raw data snapshots
  - interim/    # Cleaned but not fully modeled data
  - processed/  # Final modeling-ready datasets
  - features/   # Feature tables and feature store outputs
  - external/   # Third-party datasets
- notebooks/
  - 00_exploration/  # Quick data checks and scratch work
  - 01_eda/          # Exploratory analysis
  - 02_features/     # Feature engineering notebooks
  - 03_modeling/     # Model training notebooks
  - 04_evaluation/   # Metrics and validation notebooks
  - 05_dashboard/    # Charts prepared for the demo app
  - experiments/     # Ad-hoc experiments
- src/
  - etl/        # Ingest, clean, and transform pipelines
  - features/   # Feature engineering code
  - models/     # Training and inference utilities
  - evaluation/ # Metrics, validation, and reporting
  - viz/        # Shared plotting utilities
  - utils/      # Shared helpers
  - config/     # Config loaders and environment settings
- scraping/     # Existing scraping code can be moved here
- scripts/      # CLI entry points and batch jobs
- dashboard/    # Demo app (Streamlit/Dash) and assets
  - pages/
  - assets/
- reports/
  - figures/
  - tables/
- docs/         # Project documentation

## Suggested workflow

1. Place CSVs in data/incoming/ and move immutable snapshots to data/raw/.
2. Clean and merge data into data/interim/, then finalize datasets in data/processed/.
3. Generate features into data/features/.
4. Train models and save evaluation artifacts in reports/.
5. Build the demo in dashboard/ using outputs from data/processed/ and data/features/.
