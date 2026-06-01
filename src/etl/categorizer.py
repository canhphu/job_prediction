"""Categorize job titles into 27 standard groups.

Handles both English and Vietnamese titles, including TopCV's
glued-text format (e.g. "WebFrontendTeam Leader", "Kỹ Sư AIThị Giác").
"""

import re


# Categories with regex patterns (order matters — first match wins)
# Uses mix of \b (word boundary) and non-boundary patterns for Vietnamese/glued text
CATEGORIES = [
    # Specific roles first
    ("Blockchain Developer", r'(blockchain|web3|solidity|smart contract|crypto)'),
    ("Game Developer", r'(game\s*developer|game\s*producer|unity|unreal|3d artist|2d artist|game\s*design)'),
    ("Embedded Engineer", r'(embedded|firmware|iot|hardware|rtos|arduino|plc|nhúng|lập trình nhúng)'),
    ("Database Administrator", r'(database admin|dba|db admin|cơ sở dữ liệu|quản trị cơ sở dữ liệu)'),

    # Data roles
    ("Data Engineer", r'(data engineer|etl|data pipeline|data platform|data warehouse|data integration|data architecture|dữ liệu và báo cáo)'),
    ("AI/ML Engineer", r'(ai engineer|ml engineer|machine learning|deep learning|nlp|computer vision|data scientist|llm|artificial intelligence|trí tuệ nhân tạo|thị giác máy tính|\bai\b|ai expert)'),
    ("Data Analyst", r'(data analyst|bi analyst|business intelligence|power bi|tableau|phân tích dữ liệu|xử lý dữ liệu|chuyên viên dữ liệu)'),

    # Dev roles (specific)
    ("Mobile Developer", r'(mobile|ios|android|react native|flutter|xamarin|ionic)'),
    ("Frontend Developer", r'(frontend|front-end|front end|reactjs|vuejs|angularjs|ui developer|typescript\s*react|lập trình.*frontend)'),
    ("Backend Developer", r'(backend|back-end|back end|java developer|java dev|\.net developer|\.net|php developer|python developer|node\.?js developer|golang developer|ruby developer|c\+\+ developer|java senior|senior java|java engineer|c#|lập trình web|lập trình viên.*\.net|lập trình viên.*c#)'),
    ("Fullstack/Software Engineer", r'(fullstack|full-stack|full stack|software engineer|software developer|programmer|software development|programming|technical lead|tech lead|technical leader|software specialist|lập trình viên|phần mềm|kiến trúc sư phần mềm)'),

    # Infrastructure
    ("DevOps/Infra Engineer", r'(devops|devsecops|sre|site reliability|infrastructure|cicd|ci/cd)'),
    ("Cloud Engineer", r'(cloud engineer|cloud specialist|aws engineer|azure engineer|gcp engineer|\bcloud\b)'),
    ("Security Engineer", r'(security|cybersecurity|infosec|penetration|soc|information security|an ninh thông tin|bảo mật|an ninh mạng)'),
    ("System/Network Admin", r'(network\s*engineer|network\s*admin|system\s*admin|sysadmin|system\s*engineer|network\s*administration|it staff|it helpdesk|it system|it engineer|it specialist|hệ thống|vận hành|quản trị hệ thống|quản trị mạng|server|mạng|nhân viên it|kỹ sư hệ thống)'),
    ("IT Support", r'(it support|technical support|help desk|support engineer|hỗ trợ kỹ thuật|kỹ thuật hỗ trợ|it local support|it operations|it maintenance)'),

    # Architecture & Consulting
    ("Solution Architect", r'(architect|solution architect|technical architect|enterprise architect|kiến trúc sư|kiến trúc giải pháp)'),
    ("ERP/CRM Specialist", r'(sap|erp|crm|salesforce|odoo|dynamics 365|core banking)'),
    ("Consultant", r'(consultant|consulting|advisory|tư vấn giải pháp|tư vấn triển khai|triển khai.*phần mềm)'),

    # Management & Analysis
    ("Project Manager", r'(project manager|project coordinator|scrum master|agile coach|delivery manager|project leader|quản lý dự án|giám sát dự án)'),
    ("Product Manager/Owner", r'(product manager|product owner|product executive|product development|phát triển sản phẩm)'),
    ("Business Analyst", r'(business analyst|digital transformation|phân tích nghiệp vụ|nghiệp vụ)'),
    ("IT Manager", r'(it manager|it director|cto|cio|head of it|head of technology|head of engineering|director of|it supervisor|trưởng phòng kỹ thuật|trưởng phòng cntt|trưởng phòng công nghệ|giám đốc)'),

    # QA
    ("QA/Tester", r'(qa|qc|tester|testing|test engineer|sdet|quality assurance|quality control|test lead|kiểm thử|manual tester|quality lead)'),

    # Design
    ("UI/UX Designer", r'(ui|ux|designer|graphic|creative|design|artist|thiết kế|đồ họa|họa viên|diễn hoạt|animation)'),

    # Sales
    ("Sales/Presales", r'(sales|presales|pre-sales|account manager|business development|kinh doanh|e-commerce|ecom|tư vấn.*bán hàng|bán hàng)'),

    # IT Governance/Risk/Compliance → IT Manager
    ("IT Manager", r'(governance|compliance|risk management|audit|tuân thủ|rủi ro)'),

    # Generic management (catch remaining managers)
    ("IT Manager", r'(manager|director|head of|chief|vp|vice president|supervisor|trưởng nhóm|trưởng phòng|trưởng bộ phận|quản lý)'),

    # Vietnamese IT generic roles
    ("System/Network Admin", r'(công nghệ thông tin|cntt|it nhân viên)'),
    ("Fullstack/Software Engineer", r'(thực tập sinh.*(?:it|cntt|công nghệ)|thực tập.*(?:java|nodejs|python))'),

    # Catch remaining dev/engineer keywords (no word boundary needed)
    ("Fullstack/Software Engineer", r'(developer|engineer|dev\b|kỹ sư|lập trình)'),
    ("QA/Tester", r'(kiểm tra chất lượng)'),
    ("Data Analyst", r'(quản trị thông tin)'),
    ("Consultant", r'(tư vấn)'),
]


def categorize_title(title: str) -> str:
    """Categorize a job title into one of 27 standard groups.
    
    Handles glued text from TopCV (e.g. "WebFrontendTeam Leader")
    by inserting spaces before uppercase letters for better matching.
    """
    if not title:
        return "Other"
    
    title_lower = title.lower()
    
    # Also try with spaces inserted before uppercase (handles TopCV glued text)
    # "WebFrontendTeam Leader" → "web frontend team leader"
    title_spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', title).lower()
    
    for category, pattern in CATEGORIES:
        if re.search(pattern, title_lower) or re.search(pattern, title_spaced):
            return category
    return "Other"
