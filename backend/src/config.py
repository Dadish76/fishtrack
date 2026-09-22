"""
Модуль конфигурации приложения.
"""
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv("/etc/fishtrack/.env")


class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/fishtrack")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
