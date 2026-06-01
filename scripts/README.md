# Scripts

CLI entry points cho pipeline. Chạy từ project root.

## Danh sách scripts

| Script | Mục đích | Input | Output |
|--------|----------|-------|--------|
| `run_crawlers.py` | Crawl dữ liệu | Web | `data/raw/{nguồn}_{date}.csv` |
| `run_etl.py` | Clean + append | `data/raw/*.csv` | `data/interim/` + `data/processed/jobs_cleaned_full.csv` |
| `run_features.py` | Feature engineering | `data/processed/jobs_cleaned_full.csv` | `data/features/jobs_featured_full.csv` |
| `run_pipeline.py` | End-to-end | Web | Tất cả output trên |

## Cách dùng

### Crawl

```bash
python scripts/run_crawlers.py --all --max-pages 5
python scripts/run_crawlers.py --source topcv --max-pages 3
python scripts/run_crawlers.py --source linkedin --max-pages 10
```

### ETL

```bash
# Xử lý file raw mới (chưa xử lý)
python scripts/run_etl.py

# Xử lý lại toàn bộ từ đầu
python scripts/run_etl.py --reprocess-all
```

### Feature Engineering

```bash
python scripts/run_features.py
```

### Full Pipeline

```bash
# Crawl + ETL + Features
python scripts/run_pipeline.py --all --max-pages 5

# Chỉ ETL + Features (dùng raw có sẵn)
python scripts/run_pipeline.py --skip-crawl --all
```

## Tracking

File `logs/processed_files.json` lưu danh sách file raw đã qua ETL.
Khi chạy `run_etl.py`, chỉ xử lý file mới chưa có trong danh sách.
