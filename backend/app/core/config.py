from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "IMAGINA V1"
    app_version: str = "1.0.0"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./data/imagina.db"
    cors_origins: str = "http://localhost:3000"
    max_session_duration_seconds: int = 1200  # 20 minutes
    window_interval_seconds: float = 2.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
