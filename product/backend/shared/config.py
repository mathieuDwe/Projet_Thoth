from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Thoth OSINT Platform"
    debug: bool = False
    db_url: str = "sqlite+aiosqlite:///./data/thoth.db"
    redis_url: str = "redis://redis:6379/0"
    log_level: str = "INFO"

    breach_db_path: str = "/data/breach_db.json"
    shodan_api_key: str = ""
    virustotal_api_key: str = ""
    abuseipdb_api_key: str = ""
    ipinfo_api_key: str = ""
    proxy_url: str = ""

    max_timeout: int = 30
    max_retries: int = 3
    rate_limit_rps: float = 2.0

    report_storage_path: str = "/data/reports"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
