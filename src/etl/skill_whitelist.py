"""white list ~150 valid skills"""

VALID_SKILLS = {
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "c",
    "go", "golang", "rust", "ruby", "php", "swift", "kotlin", "scala",
    "r", "perl", "matlab", "lua", "dart", "elixir", "haskell",
    "objective-c", "vba", "shell", "bash", "powershell",
    # Frontend frameworks
    "react", "angular", "vue", "vue.js", "next.js", "nuxt", "svelte",
    "jquery", "bootstrap", "material ui",
    # Backend frameworks
    "node.js", "express", "django", "flask", "fastapi",
    "spring", "spring boot", ".net", "asp.net", "laravel", "symfony",
    "rails", "ruby on rails", "nestjs",
    # Mobile
    "ios", "android", "react native", "flutter", "xamarin", "ionic",
    # Cloud & DevOps
    "docker", "kubernetes", "k8s", "aws", "azure", "gcp",
    "terraform", "ansible", "jenkins", "gitlab ci", "github actions",
    "ci/cd", "devops", "helm", "argocd", "prometheus", "grafana",
    "nginx", "apache",
    # Databases
    "sql", "nosql", "mongodb", "postgresql", "mysql", "redis",
    "elasticsearch", "kibana", "kafka", "rabbitmq",
    "oracle", "sql server", "sqlite", "dynamodb", "cassandra",
    "neo4j", "mariadb", "mssql",
    # Data & AI/ML
    "machine learning", "deep learning", "nlp", "ai",
    "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn",
    "spark", "hadoop", "airflow", "dbt", "snowflake", "databricks",
    "power bi", "tableau", "looker",
    "computer vision", "opencv", "llm",
    # Web technologies
    "html", "html5", "css", "css3", "sass", "tailwind",
    "webpack", "vite", "graphql", "rest", "restful",
    "grpc", "websocket", "oauth", "jwt", "api", "sdk",
    # Version control & collaboration
    "git", "svn", "jira", "confluence",
    # Testing
    "selenium", "cypress", "jest", "junit", "pytest",
    "postman", "swagger", "automation test",
    # Design
    "figma", "sketch", "adobe", "photoshop",
    # Methodologies
    "agile", "scrum", "kanban", "tdd", "oop",
    "design patterns", "solid", "microservices",
    # Infrastructure & Networking
    "linux", "unix", "windows server",
    "networking", "firewall", "vpn", "security", "cybersecurity",
    "tcp/ip", "dns", "vmware", "hyper-v",
    "active directory", "ldap", "sso", "itil",
    # Enterprise software
    "sap", "salesforce", "servicenow", "erp", "crm",
    "sharepoint", "dynamics 365", "odoo",
    # Blockchain
    "blockchain", "web3", "solidity", "ethereum", "smart contract",
    # Other
    "excel", "shopify", "wordpress",
    "embedded", "iot", "rtos", "arduino",
    "project management", "pmp",
    "english", "japanese", "korean",
    "bi", "ssis", "ssrs",
}

SKILL_ALIASES = {
    "golang": "Go", "k8s": "Kubernetes",
    "react.js": "React", "reactjs": "React",
    "vue.js": "Vue", "vuejs": "Vue",
    "node.js": "Node.js", "nodejs": "Node.js",
    "next.js": "Next.js", "nextjs": "Next.js",
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mongodb": "MongoDB", "mongo": "MongoDB",
    "amazon web services": "AWS",
    "google cloud": "GCP", "microsoft azure": "Azure",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "ci/cd": "CI/CD", "restful": "REST", "restful api": "REST",
}