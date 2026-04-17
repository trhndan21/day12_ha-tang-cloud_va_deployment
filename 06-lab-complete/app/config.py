from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Production Agent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # Security
    AGENT_API_KEY: str = "secret-key-123"
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Agent Logic
    RATE_LIMIT_PER_MINUTE: int = 10
    MONTHLY_BUDGET_USD: float = 10.0
    LLM_MODEL: str = "gpt-4o-mini"
    
    # OpenAI (Optional)
    OPENAI_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
