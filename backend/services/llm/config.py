import os

class Settings:
    APP_NAME = "RevMine LLM Service"
    APP_VERSION = "1.0.0"
    DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "deepseek-r1")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama-service:11434")
    OPENROUTER_API_KEY= os.getenv("OPENROUTER_API_KEY", "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")
    OPENROUTER_SITE_URL: str | None = None


settings = Settings()
