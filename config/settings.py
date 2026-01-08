"""
Application configuration and settings
"""

import os
from dotenv import load_dotenv
from typing import Optional


load_dotenv()


class Settings:
    """
    Application settings loaded from environment variables
    """

    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # Application
    APP_NAME: str = os.getenv("APP_NAME", "AI Command Center")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))

    # Models
    DEFAULT_LLM_MODEL: str = "claude-sonnet-4-5-20250929"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "100"))
    RATE_LIMIT_PER_DAY: int = int(os.getenv("RATE_LIMIT_PER_DAY", "1000"))

    # Monitoring
    ENABLE_MONITORING: bool = os.getenv("ENABLE_MONITORING", "True").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Paths
    VECTOR_DB_PATH: str = os.getenv("VECTOR_DB_PATH", "./data/vector_db")
    DOCUMENTS_PATH: str = "./data/documents"

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

    # Costs (per 1M tokens)
    CLAUDE_INPUT_COST: float = 3.0
    CLAUDE_OUTPUT_COST: float = 15.0
    GPT4_INPUT_COST: float = 2.5
    GPT4_OUTPUT_COST: float = 10.0
    EMBEDDING_COST: float = 0.02
    
    # API Configuration
    API_KEY: str = os.getenv("API_KEY", "dev-key-change-in-production")
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8501"]  # Streamlit
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    @classmethod
    def validate(cls) -> bool:
        """Validate required settings"""
        required = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
        missing = [key for key in required if not getattr(cls, key)]

        if missing:
            raise ValueError(f"Missing required settings: {missing}")

        return True


# Initialize and validate
settings = Settings()

if __name__ == "__main__":
    try:
        settings.validate()
        print("✅ Settings validated successfully")
        print(f"App: {settings.APP_NAME}")
        print(f"Debug: {settings.DEBUG}")
        print(f"Rate Limit: {settings.RATE_LIMIT_PER_HOUR}/hour")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
