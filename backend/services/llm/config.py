import os


class Settings:
    APP_NAME = "RevMine LLM Service"
    APP_VERSION = "1.0.0"
    DEFAULT_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "deepseek-r1")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_DEFAULT_MODEL = os.getenv("OPENROUTER_DEFAULT_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_SITE_URL: str | None = None


settings = Settings()
