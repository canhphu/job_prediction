"""Categorize job tiles into 27 standard groups"""

import re


CATEGORIES = [
    ("Blockchain Developer", r'\b(blockchain|web3|solidity|smart contract|crypto)\b'),
    ("Game Developer", r'\b(game|unity|unreal|3d artist|2d artist)\b'),
    ("Embedded Engineer", r'\b(embedded|firmware|iot|hardware|rtos|arduino|plc)\b'),
    ("Database Administrator", r'\b(database admin|dba|db admin)\b'),
    ("Data Engineer", r'\b(data engineer|etl|data pipeline|data platform|data warehouse)\b'),
    ("AI/ML Engineer", r'\b(ai engineer|ml engineer|machine learning|deep learning|nlp|computer vision|data scientist|llm|\bai\b)\b'),
    ("Data Analyst", r'\b(data analyst|bi analyst|business intelligence|power bi|tableau)\b'),
    ("Mobile Developer", r'\b(mobile|ios|android|react native|flutter|xamarin)\b'),
    ("Frontend Developer", r'\b(frontend|front-end|front end|reactjs|vuejs|angularjs|ui developer)\b'),
    ("Backend Developer", r'\b(backend|back-end|back end|java developer|\.net developer|php developer|python developer|node\.?js developer|golang developer)\b'),
    ("Fullstack/Software Engineer", r'\b(fullstack|full-stack|full stack|software engineer|software developer|programmer|technical lead|tech lead)\b'),
    ("DevOps/Infra Engineer", r'\b(devops|devsecops|sre|site reliability|infrastructure|cicd|ci/cd)\b'),
    ("Cloud Engineer", r'\b(cloud engineer|cloud specialist|aws engineer|azure engineer|gcp engineer|cloud)\b'),
    ("Security Engineer", r'\b(security|cybersecurity|infosec|penetration|soc|information security)\b'),
    ("System/Network Admin", r'\b(network engineer|network admin|system admin|sysadmin|system engineer|it staff|it helpdesk)\b'),
    ("IT Support", r'\b(it support|technical support|help desk|support engineer)\b'),
    ("Solution Architect", r'\b(architect|solution architect|technical architect|enterprise architect)\b'),
    ("ERP/CRM Specialist", r'\b(sap|erp|crm|salesforce|odoo|dynamics 365)\b'),
    ("Consultant", r'\b(consultant|consulting|advisory)\b'),
    ("Project Manager", r'\b(project manager|project coordinator|scrum master|agile coach|delivery manager)\b'),
    ("Product Manager/Owner", r'\b(product manager|product owner|product executive)\b'),
    ("Business Analyst", r'\b(business analyst|digital transformation)\b'),
    ("IT Manager", r'\b(it manager|it director|cto|cio|head of it|head of technology|head of engineering)\b'),
    ("QA/Tester", r'\b(qa|qc|tester|testing|test engineer|sdet|quality assurance)\b'),
    ("UI/UX Designer", r'\b(ui|ux|designer|graphic|creative|design)\b'),
    ("Sales/Presales", r'\b(sales|presales|pre-sales|account manager|business development)\b'),
    ("IT Manager", r'\b(manager|director|head of|chief|supervisor)\b'),
    ("Fullstack/Software Engineer", r'\b(developer|engineer|dev\b)\b'),
]

def categorize_title(title: str) -> str:
    title_lower = title.lower()
    for category, pattern in CATEGORIES:
        if re.search(pattern, title_lower):
            return category
    return "Other"
