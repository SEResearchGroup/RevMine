import os

class Settings:
    APP_NAME = "RevMine LLM Service"
    APP_VERSION = "1.0.0"
    DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "deepseek-r1")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama-service:11434")
    OPENROUTER_API_KEY= os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_SITE_URL: str | None = None


settings = Settings()
