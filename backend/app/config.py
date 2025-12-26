"""
Application Configuration
"""
from functools import lru_cache
from dataclasses import dataclass


@dataclass
class Settings:
    # Application
    APP_NAME: str = "农链溯源 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database (使用 SQLite 开发, 生产环境改为 MySQL)
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "123123"
    DB_NAME: str = "agri_trace"
    USE_SQLITE: bool = True  # 开发模式使用 SQLite

    @property
    def DATABASE_URL(self) -> str:
        if self.USE_SQLITE:
            return "sqlite:///./agri_trace.db"
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production-agri-trace-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # FISCO BCOS
    FISCO_NODE_HOST: str = "127.0.0.1"
    FISCO_NODE_PORT: int = 20200
    FISCO_GROUP_ID: int = 1


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
