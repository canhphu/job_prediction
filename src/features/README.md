# Features

Module tạo features cho ML modeling từ dữ liệu đã clean.

## Files

| File | Mục đích |
|------|----------|
| `feature_engineer.py` | Pipeline tạo ~73 columns features |

## Feature Groups

| Nhóm | Số cột | Mô tả |
|------|--------|--------|
| Metadata | 7 | job_title, company_name, posted_date, source, salary_min, salary_max, salary_missing |
| Target | 2 | salary_avg, salary_range |
| Numeric | 2 | experience_required, skill_count |
| Bucket | 1 | experience_bucket |
| Time | 2 | posted_month, posted_week |
| Skills multi-hot | 20 | skill_AI, skill_SQL, ..., skill_JavaScript |
| Domain flags | 4 | has_cloud, has_ai_ml, has_devops, has_data |
| Job level one-hot | 5 | job_level_Intern, ..., job_level_ManagerPlus |
| Location one-hot | 4 | location_Hanoi, location_HCM, location_DaNang, location_Other |
| Category one-hot | 27 | cat_Fullstack, cat_UIUX, ..., cat_Blockchain |

## Salary Range Buckets

| Bucket | Điều kiện | Ý nghĩa |
|--------|-----------|----------|
| <10M | salary_avg < 10M | Entry/Intern |
| 10-15M | 10M ≤ avg < 15M | Junior |
| 15-20M | 15M ≤ avg < 20M | Mid (low) |
| 20-30M | 20M ≤ avg < 30M | Mid (high) |
| 30-50M | 30M ≤ avg < 50M | Senior |
| >50M | avg ≥ 50M | Lead/Manager+ |

## Top 20 Skills (Multi-hot)

AI, SQL, Java, API, Python, Excel, Agile, REST, Security, CI/CD,
AWS, Linux, Docker, Scrum, ERP, DevOps, Git, React, CRM, JavaScript

## Cách chạy

```bash
python scripts/run_features.py
```

Input: `data/processed/jobs_cleaned_full.csv`
Output: `data/features/jobs_featured_full.csv`
