# Phân tích và Dự đoán Xu hướng Tuyển dụng Ngành IT

## 1. Tên dự án

**"IT Job Market Analytics — Phân tích và Dự đoán Xu hướng Tuyển dụng Ngành Công nghệ Thông tin tại Việt Nam"**

---

## 2. Bài toán

### 2.1. Mô tả bài toán

Thị trường tuyển dụng ngành IT thay đổi nhanh chóng với sự xuất hiện liên tục của các công nghệ mới. Dự án này nhằm:

- **Phân tích hiện trạng** thị trường tuyển dụng IT tại Việt Nam (kỹ năng được yêu cầu, mức lương, phân bố theo khu vực, kinh nghiệm, v.v.)
- **Dự đoán xu hướng** tuyển dụng trong tương lai: kỹ năng nào sẽ tăng/giảm nhu cầu, mức lương dự kiến, vị trí nào sẽ "hot"

### 2.2. Câu hỏi nghiên cứu

1. Những kỹ năng/công nghệ nào đang được yêu cầu nhiều nhất trong ngành IT?
2. Mức lương trung bình theo vị trí, kinh nghiệm và khu vực như thế nào?
3. Xu hướng nhu cầu tuyển dụng thay đổi ra sao theo thời gian?
4. Có thể dự đoán mức lương dựa trên kỹ năng, kinh nghiệm và vị trí không?
5. Những kỹ năng nào sẽ có xu hướng tăng trưởng trong 6–12 tháng tới?

---

## 3. Dữ liệu (Input)

### 3.1. Nguồn dữ liệu

| Nguồn | Mô tả | Phương pháp thu thập |
|---|---|---|
| **TopCV** (topcv.vn) | Trang tuyển dụng lớn tại VN | Web scraping (BeautifulSoup/Selenium) |
| **ITviec** (itviec.com) | Chuyên tuyển dụng IT | Web scraping |
| **LinkedIn Jobs** | Tuyển dụng quốc tế & VN | LinkedIn API / scraping |
| **CareerBuilder VN** | Trang tuyển dụng tổng hợp | Web scraping |
| **Stack Overflow Survey** | Khảo sát developer hàng năm | Dataset công khai (CSV) |
| **Kaggle Datasets** | Các dataset tuyển dụng IT có sẵn | Download trực tiếp |

### 3.2. Các trường dữ liệu cần thu thập

```
- job_title          : Tên vị trí tuyển dụng
- company_name       : Tên công ty
- company_size       : Quy mô công ty
- location           : Địa điểm làm việc (tỉnh/thành phố)
- salary_min         : Mức lương tối thiểu
- salary_max         : Mức lương tối đa
- salary_currency    : Đơn vị tiền tệ (VND/USD)
- experience_required: Số năm kinh nghiệm yêu cầu
- skills             : Danh sách kỹ năng yêu cầu
- job_type           : Loại hình (Full-time/Part-time/Remote/Hybrid)
- job_level          : Cấp bậc (Junior/Mid/Senior/Lead/Manager)
- posted_date        : Ngày đăng tin
- deadline           : Hạn nộp hồ sơ
- job_description    : Mô tả công việc (text)
- benefits           : Phúc lợi
- source             : Nguồn dữ liệu
```

### 3.3. Quy mô dữ liệu mục tiêu

- **Tối thiểu**: 5,000 – 10,000 tin tuyển dụng
- **Lý tưởng**: 20,000+ tin tuyển dụng, thu thập trong khoảng 3–6 tháng để có dữ liệu theo thời gian

---

## 4. Phương pháp và Mô hình

### 4.1. Tiền xử lý dữ liệu

- Làm sạch dữ liệu: xử lý missing values, loại bỏ duplicates
- Chuẩn hóa mức lương về cùng đơn vị (VND/tháng)
- Trích xuất kỹ năng từ job description bằng NLP (keyword extraction, NER)
- Phân loại job level từ job title (regex + rule-based + ML)
- Encoding các biến phân loại (One-Hot, Label Encoding)

### 4.2. Phân tích khám phá dữ liệu (EDA)

| Phân tích | Kỹ thuật |
|---|---|
| Phân bố lương theo vị trí | Box plot, Violin plot |
| Top kỹ năng được yêu cầu | Bar chart, Word cloud |
| Phân bố việc làm theo khu vực | Choropleth map (Folium) |
| Tương quan kỹ năng – lương | Heatmap, Scatter plot |
| Xu hướng theo thời gian | Line chart, Time series |
| Mạng lưới kỹ năng liên quan | Network graph (NetworkX) |

### 4.3. Mô hình dự đoán

#### A. Dự đoán mức lương (Regression)

| Mô hình | Mô tả |
|---|---|
| **Linear Regression** | Baseline model |
| **Random Forest Regressor** | Ensemble, xử lý tốt non-linear |
| **Gradient Boosting (XGBoost/LightGBM)** | Hiệu suất cao, phổ biến trong tabular data |
| **Neural Network (MLP)** | Deep learning cho dữ liệu phức tạp |

- **Input features**: skills (multi-hot encoded), experience, location, company_size, job_level
- **Target**: salary (trung bình của salary_min và salary_max)

#### B. Dự đoán xu hướng kỹ năng (Time Series)

| Mô hình | Mô tả |
|---|---|
| **ARIMA/SARIMA** | Mô hình chuỗi thời gian cổ điển |
| **Prophet (Facebook)** | Dự đoán chuỗi thời gian với seasonality |
| **LSTM** | Deep learning cho sequence data |

- **Input**: Số lượng tin tuyển dụng yêu cầu kỹ năng X theo tuần/tháng
- **Target**: Số lượng dự đoán trong các tháng tiếp theo

#### C. Phân cụm vị trí tuyển dụng (Clustering)

| Mô hình | Mô tả |
|---|---|
| **K-Means** | Phân cụm cơ bản |
| **DBSCAN** | Phân cụm dựa trên mật độ |
| **Hierarchical Clustering** | Phân cụm phân cấp |

- **Mục đích**: Nhóm các vị trí tuyển dụng tương tự nhau để phát hiện các "nhóm nghề" trong ngành IT

---

## 5. Đầu ra (Output)

### 5.1. Kết quả phân tích

- **Báo cáo EDA** chi tiết với biểu đồ trực quan
- **Bảng xếp hạng kỹ năng** được yêu cầu nhiều nhất (top 20–30)
- **Bản đồ lương** theo khu vực và vị trí
- **Biểu đồ xu hướng** kỹ năng theo thời gian

### 5.2. Mô hình dự đoán

- Mô hình dự đoán mức lương khi nhập kỹ năng + kinh nghiệm + khu vực
- Mô hình dự đoán xu hướng kỹ năng trong 3–6 tháng tới
- Phân cụm các nhóm nghề IT

### 5.3. Sản phẩm cuối

- **Dashboard tương tác** (Streamlit hoặc Power BI) bao gồm:
  - Bộ lọc theo khu vực, kỹ năng, mức lương, kinh nghiệm
  - Biểu đồ xu hướng real-time
  - Công cụ dự đoán lương (nhập thông tin → trả về mức lương dự kiến)
  - Bản đồ phân bố việc làm
- **Báo cáo PDF** tổng hợp kết quả nghiên cứu
- **Source code** trên GitHub với documentation đầy đủ

---

## 6. Cách đánh giá

### 6.1. Đánh giá mô hình Regression (Dự đoán lương)

| Metric | Mô tả | Mục tiêu |
|---|---|---|
| **MAE** (Mean Absolute Error) | Sai số tuyệt đối trung bình | Càng thấp càng tốt |
| **RMSE** (Root Mean Squared Error) | Căn bậc hai sai số bình phương TB | Càng thấp càng tốt |
| **R² Score** | Tỷ lệ phương sai được giải thích | ≥ 0.7 |
| **MAPE** (Mean Absolute % Error) | Sai số phần trăm trung bình | ≤ 15% |

### 6.2. Đánh giá mô hình Time Series (Xu hướng kỹ năng)

| Metric | Mô tả |
|---|---|
| **MAE / RMSE** | Sai số dự đoán số lượng tin tuyển dụng |
| **MAPE** | Sai số phần trăm |
| **Visual comparison** | So sánh đồ thị dự đoán vs thực tế |

### 6.3. Đánh giá mô hình Clustering

| Metric | Mô tả |
|---|---|
| **Silhouette Score** | Đo chất lượng phân cụm (−1 đến 1, càng cao càng tốt) |
| **Elbow Method** | Xác định số cụm tối ưu |
| **Davies-Bouldin Index** | Đo độ tách biệt giữa các cụm |

### 6.4. Đánh giá tổng thể dự án

- Cross-validation (K-Fold = 5) cho tất cả mô hình
- So sánh hiệu suất giữa các mô hình (model comparison table)
- A/B testing với dữ liệu mới (train trên dữ liệu cũ, test trên dữ liệu mới thu thập)

---

## 7. Cách thực hiện chi tiết

### 7.1. Công nghệ sử dụng

```
Ngôn ngữ       : Python 3.10+
Thu thập DL     : BeautifulSoup, Selenium, Scrapy, requests
Xử lý DL       : Pandas, NumPy
Trực quan hóa   : Matplotlib, Seaborn, Plotly, Folium
NLP             : underthesea (tiếng Việt), spaCy, regex
Machine Learning: scikit-learn, XGBoost, LightGBM
Time Series     : statsmodels, Prophet, TensorFlow/Keras (LSTM)
Dashboard       : Streamlit
Quản lý code    : Git + GitHub
Môi trường      : Jupyter Notebook + VS Code
```

### 7.2. Kế hoạch thực hiện (12 tuần)

#### Giai đoạn 1: Thu thập dữ liệu (Tuần 1–3)

| Tuần | Công việc | Người phụ trách |
|---|---|---|
| 1 | Khảo sát nguồn dữ liệu, thiết kế schema | Cả nhóm |
| 1–2 | Viết script crawl TopCV, ITviec | Thành viên 1 + 2 |
| 2–3 | Crawl LinkedIn, CareerBuilder | Thành viên 1 + 2 |
| 3 | Tổng hợp, kiểm tra chất lượng dữ liệu thô | Thành viên 3 |

#### Giai đoạn 2: Tiền xử lý & EDA (Tuần 4–6)

| Tuần | Công việc | Người phụ trách |
|---|---|---|
| 4 | Làm sạch dữ liệu, xử lý missing values | Thành viên 3 |
| 4–5 | Trích xuất kỹ năng từ job description (NLP) | Thành viên 4 |
| 5–6 | Phân tích khám phá (EDA), tạo biểu đồ | Thành viên 5 |
| 6 | Feature engineering | Thành viên 3 + 4 |

#### Giai đoạn 3: Xây dựng mô hình (Tuần 7–9)

| Tuần | Công việc | Người phụ trách |
|---|---|---|
| 7 | Xây dựng mô hình dự đoán lương | Thành viên 3 + 4 |
| 8 | Xây dựng mô hình dự đoán xu hướng kỹ năng | Thành viên 4 |
| 8 | Xây dựng mô hình phân cụm | Thành viên 3 |
| 9 | Tuning hyperparameters, so sánh mô hình | Thành viên 3 + 4 |

#### Giai đoạn 4: Dashboard & Triển khai (Tuần 10–11)

| Tuần | Công việc | Người phụ trách |
|---|---|---|
| 10 | Thiết kế và xây dựng dashboard Streamlit | Thành viên 1 + 2 |
| 10 | Tích hợp mô hình vào dashboard | Thành viên 4 |
| 11 | Testing, fix bugs, tối ưu UI/UX | Thành viên 1 + 2 |

#### Giai đoạn 5: Báo cáo & Thuyết trình (Tuần 12)

| Tuần | Công việc | Người phụ trách |
|---|---|---|
| 12 | Viết báo cáo tổng hợp | Thành viên 5 |
| 12 | Chuẩn bị slide thuyết trình | Thành viên 5 |
| 12 | Review code, viết README, đóng gói project | Cả nhóm |
| 12 | Thuyết trình & demo | Cả nhóm |

### 7.3. Phân công nhóm 5 người

| Thành viên | Vai trò chính | Nhiệm vụ |
|---|---|---|
| **Thành viên 1** | Data Engineer | Viết crawler, thu thập dữ liệu, xây pipeline, phát triển dashboard |
| **Thành viên 2** | Data Engineer | Hỗ trợ crawl, quản lý database, phát triển dashboard |
| **Thành viên 3** | Data Analyst | Tiền xử lý, EDA, feature engineering, xây mô hình clustering |
| **Thành viên 4** | ML Engineer | Xây dựng & tối ưu mô hình ML, NLP, tích hợp mô hình |
| **Thành viên 5** | Visualization & Report | Trực quan hóa, viết báo cáo, chuẩn bị thuyết trình |

### 7.4. Cấu trúc thư mục dự án

```
it-job-market-analytics/
├── data/
│   ├── raw/                  # Dữ liệu thô từ crawling
│   ├── processed/            # Dữ liệu đã xử lý
│   └── external/             # Dữ liệu từ nguồn bên ngoài (Kaggle, SO Survey)
├── notebooks/
│   ├── 01_data_collection.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_eda.ipynb
│   ├── 04_feature_engineering.ipynb
│   ├── 05_salary_prediction.ipynb
│   ├── 06_trend_forecasting.ipynb
│   └── 07_clustering.ipynb
├── src/
│   ├── crawlers/             # Scripts crawl dữ liệu
│   │   ├── topcv_crawler.py
│   │   ├── itviec_crawler.py
│   │   └── linkedin_crawler.py
│   ├── preprocessing/        # Scripts tiền xử lý
│   │   ├── cleaner.py
│   │   └── skill_extractor.py
│   ├── models/               # Mô hình ML
│   │   ├── salary_model.py
│   │   ├── trend_model.py
│   │   └── clustering_model.py
│   └── utils/                # Hàm tiện ích
│       └── helpers.py
├── dashboard/
│   └── app.py                # Streamlit dashboard
├── reports/
│   ├── figures/              # Biểu đồ xuất ra
│   └── final_report.pdf
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 8. Rủi ro và Giải pháp

| Rủi ro | Giải pháp |
|---|---|
| Website chặn crawling | Sử dụng proxy rotation, delay giữa các request, tuân thủ robots.txt |
| Dữ liệu lương bị ẩn ("Thỏa thuận") | Xây mô hình imputation hoặc loại bỏ, ghi nhận tỷ lệ missing |
| Dữ liệu không đủ lớn | Kết hợp nhiều nguồn, sử dụng thêm dataset Kaggle |
| Kỹ năng viết nhiều cách khác nhau | Xây bảng mapping chuẩn hóa (ví dụ: JS = JavaScript = javascript) |
| Mô hình dự đoán kém | Thử nhiều mô hình, feature engineering kỹ hơn, thu thập thêm dữ liệu |

---

## 9. Tài liệu tham khảo

- scikit-learn Documentation: https://scikit-learn.org/
- Streamlit Documentation: https://docs.streamlit.io/
- Facebook Prophet: https://facebook.github.io/prophet/
- underthesea (NLP tiếng Việt): https://github.com/undertheseanlp/underthesea
- XGBoost Documentation: https://xgboost.readthedocs.io/
- Stack Overflow Developer Survey: https://survey.stackoverflow.co/
