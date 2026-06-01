# ETL (Extract, Transform, Load)

Module làm sạch và chuẩn hóa dữ liệu raw thành format phân tích được.

## Files

| File | Mục đích |
|------|----------|
| `cleaner.py` | Pipeline cleaning chính: normalize + dedup + output 13 cột |
| `categorizer.py` | Phân loại job_title thành 27 nhóm chuẩn |
| `skill_whitelist.py` | Whitelist ~150 kỹ năng kỹ thuật + alias mapping |

## Cleaning Pipeline (`cleaner.py`)

Thứ tự xử lý:

1. Drop columns không cần: job_description, benefits, company_size, deadline
2. Loại records chất lượng thấp (title < 3 ký tự, company trống)
3. Clean job_title (bỏ noise, mã tuyển dụng, tên phòng ban)
4. Normalize location → 4 giá trị: Hanoi, Ho Chi Minh City, Da Nang, Other
5. Normalize job_type → 5 giá trị: Full-time, Part-time, Internship, Contract, Remote
6. Normalize job_level → 5 giá trị: Intern, Junior, Mid, Senior, Manager+
7. Fix mâu thuẫn title/level (title có "Senior" nhưng level = "Mid")
8. Clean salary (loại outlier < 1M hoặc > 200M VND)
9. Parse skills (chỉ giữ whitelist, apply aliases)
10. Categorize job_title → 27 nhóm
11. Dedup theo (job_title, company_name, source)

## Output Schema (13 cột)

```
job_title           # Category (27 nhóm)
company_name        # Tên công ty
location            # Hanoi / Ho Chi Minh City / Da Nang / Other
posted_date         # YYYY-MM-DD
salary_min          # VND (float hoặc null)
salary_max          # VND (float hoặc null)
salary_currency     # "VND" hoặc ""
job_type            # Full-time / Part-time / Internship / Contract / Remote
job_level           # Intern / Junior / Mid / Senior / Manager+
experience_required # Số năm (float string)
skills              # Comma-separated technical skills
source              # topcv / itviec / linkedin / careerviet
salary_missing      # True / False
```

## 27 Job Categories (`categorizer.py`)

Fullstack/Software Engineer, UI/UX Designer, AI/ML Engineer, Backend Developer,
Frontend Developer, Mobile Developer, DevOps/Infra Engineer, Cloud Engineer,
Security Engineer, System/Network Admin, IT Support, Data Engineer, Data Analyst,
QA/Tester, Project Manager, Product Manager/Owner, Business Analyst, IT Manager,
ERP/CRM Specialist, Consultant, Solution Architect, Database Administrator,
Game Developer, Embedded Engineer, Blockchain Developer, Sales/Presales, Other
