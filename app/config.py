from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FitBuddy"
    admin_title: str = "FitBuddy Admin"

    # Database
    database_url: str = "sqlite:///./fitbuddy.db"

    # Gemini API
    gemini_api_key: str | None = None

    # Gemini models
    gemini_workout_model: str = "gemini-3.8-flash"
    gemini_fast_model: str = "gemini-3.8-flash"
    # Demo mode
    demo_mode: bool = False

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()