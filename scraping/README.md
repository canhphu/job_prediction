# Scraping

Web crawlers thu thập dữ liệu tuyển dụng IT từ 4 nguồn tại Việt Nam.

## Crawlers

| File | Nguồn | Method | Output |
|------|-------|--------|--------|
| `topcv_crawler.py` | topcv.vn | Selenium/nodriver (bypass Cloudflare) | `topcv_{date}.csv` |
| `itviec_crawler.py` | itviec.com | requests + optional login | `itviec_{date}.csv` |
| `linkedin_crawler.py` | linkedin.com | Public guest API (no auth) | `linkedin_{date}.csv` |
| `careerviet_crawler.py` | careerviet.vn | requests + BeautifulSoup | `careerviet_{date}.csv` |

## Architecture

```
base_crawler.py          # Abstract base class
├── robots.txt compliance
├── Rate-limiting (min 2s delay)
├── Retry with exponential backoff
├── save_raw() → data/raw/{nguồn}_{date}.csv
└── generate_report() → CrawlReport

topcv_crawler.py         # Kế thừa BaseCrawler
itviec_crawler.py        # Kế thừa BaseCrawler
linkedin_crawler.py      # Kế thừa BaseCrawler
careerviet_crawler.py    # Kế thừa BaseCrawler
```

## Raw Schema (16 cột)

Tất cả crawlers output cùng schema:

```
job_title, company_name, company_size, location,
salary_min, salary_max, salary_currency,
experience_required, skills, job_type, job_level,
posted_date, deadline, job_description, benefits, source
```

## Cách chạy

```bash
# Chạy từ project root
python scripts/run_crawlers.py --source topcv --max-pages 5
python scripts/run_crawlers.py --all --max-pages 3
```

## Lưu ý

- TopCV cần Selenium (Edge hoặc Chrome) hoặc nodriver
- ITviec: login optional, nếu có sẽ lấy được salary
- LinkedIn: bị rate-limit sau ~50 requests, cần delay 3-5s
- CareerViet: ổn định nhất, chỉ cần requests
- Code gốc từ `it-recruitment-analysis/src/crawlers/`, đổi import path
