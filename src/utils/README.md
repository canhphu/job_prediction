# Utils

Shared utilities dùng chung cho toàn bộ project.

## Files

| File | Mục đích |
|------|----------|
| `logger.py` | Logging utility — ghi file + console |
| `data_reports.py` | Dataclasses cho crawl reporting |

## Logger (`logger.py`)

Dual output: file (`logs/pipeline.log`) + console (stderr).

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("Processing %d records", count)
```

Format:
```
2026-06-01 10:30:00 - module_name - INFO - [function_name] Message
```

## Data Reports (`data_reports.py`)

Dataclasses cho crawl session reporting:

- `CrawlError` — chi tiết 1 lỗi (url, error_code, timestamp, message)
- `CrawlReport` — tổng kết session (source, total_pages, total_records, total_errors, duration)

```python
from src.utils.data_reports import CrawlReport, CrawlError

report = crawler.generate_report()
print(f"{report.source}: {report.total_records} records in {report.duration_seconds:.1f}s")
```
