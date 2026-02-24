import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Config
    API_PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")
    
    # Execution Governance
    GLOBAL_TIMEOUT_SEC: float = float(os.getenv("GLOBAL_TIMEOUT_SEC", "15.0"))
    MAX_CONCURRENT_CHECKS: int = int(os.getenv("MAX_CONCURRENT_CHECKS", "10"))
    
    # Paths
    POLICY_PATH: str = os.getenv("POLICY_PATH", "policies/prod.yaml")
    SLO_PATH: str = os.getenv("SLO_PATH", "slos/service_levels.yaml")
    # HTTP Check
    HTTP_ENDPOINTS: List[str] = os.getenv("HTTP_ENDPOINTS", "http://localhost:8000/health/live").split(",")
    HTTP_TIMEOUT_SEC: int = int(os.getenv("HTTP_TIMEOUT_SEC", "5"))
    
    # K8s Check
    # Paths
    POLICY_PATH: str = os.getenv("POLICY_PATH", "policies/prod.yaml")
    SLO_PATH: str = os.getenv("SLO_PATH", "slos/service_levels.yaml")
    TOPOLOGY_PATH: str = os.getenv("TOPOLOGY_PATH", "policies/topology.yaml")
    
    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    DB_TIMEOUT_SEC: int = int(os.getenv("DB_TIMEOUT_SEC", "5"))
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    @property
    def async_database_url(self) -> str:
        return "sqlite+aiosqlite:///./test.db"
    
    # Resource Check
    CPU_THRESHOLD_PERCENT: float = float(os.getenv("CPU_THRESHOLD_PERCENT", "85.0"))
    MEM_THRESHOLD_PERCENT: float = float(os.getenv("MEM_THRESHOLD_PERCENT", "85.0"))
    
    # Notifier
    SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "25"))
    ALERT_EMAIL_FROM: str = os.getenv("ALERT_EMAIL_FROM", "alerts@example.com")
    ALERT_EMAIL_TO: str = os.getenv("ALERT_EMAIL_TO", "")

    class Config:
        case_sensitive = True

settings = Settings()
