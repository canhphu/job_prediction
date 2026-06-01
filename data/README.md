# Data

Dữ liệu được tổ chức theo pipeline stages, mỗi thư mục đại diện cho một giai đoạn xử lý.

## Cấu trúc

```
data/
├── raw/            # Dữ liệu thô từ crawlers (immutable)
├── interim/        # Dữ liệu đã clean riêng lẻ từng file
├── processed/      # Dataset tích lũy, sẵn sàng cho feature engineering
├── features/       # Dataset có đầy đủ features cho modeling
└── external/       # Dữ liệu từ bên thứ ba
```

## Luồng dữ liệu

```
raw/{nguồn}_{YYYY-MM-DD}.csv
    → clean + normalize
    → interim/{nguồn}_{YYYY-MM-DD}_cleaned.csv
    → append + dedup
    → processed/jobs_cleaned_full.csv
    → feature engineering
    → features/jobs_featured_full.csv
```

## Chi tiết từng folder

### raw/
- File naming: `{nguồn}_{YYYY-MM-DD}.csv` (vd: `topcv_2026-06-01.csv`)
- 16 cột raw schema
- **Không được sửa** sau khi tạo (immutable)
- Nguồn: topcv, itviec, linkedin, careerviet

### interim/
- File naming: `{nguồn}_{YYYY-MM-DD}_cleaned.csv`
- 13 cột sau khi clean
- Kết quả cleaning riêng lẻ từng file raw, dùng để kiểm tra chất lượng

### processed/
- `jobs_cleaned_full.csv` — dataset tích lũy qua nhiều lần crawl
- 13 cột: job_title, company_name, location, posted_date, salary_min, salary_max, salary_currency, job_type, job_level, experience_required, skills, source, salary_missing

### features/
- `jobs_featured_full.csv` — ~73 cột features cho ML
- Re-generate toàn bộ mỗi lần chạy `scripts/run_features.py`

### external/
- Dữ liệu bổ sung từ nguồn bên ngoài (nếu có)

## Lưu ý

- Tất cả file CSV đều bị .gitignore (quá nặng cho Git)
- Chỉ các file README.md được track
- Dùng `scripts/run_etl.py --reprocess-all` để rebuild từ đầu
