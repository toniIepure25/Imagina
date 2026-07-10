from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "IMAGINA"
    app_version: str = "0.5.0.dev1"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./data/imagina.db"
    cors_origins: str = "http://localhost:3000"
    max_session_duration_seconds: int = 1200  # 20 minutes
    window_interval_seconds: float = 2.0
    enable_experimental_lsl: bool = False
    study_mode: str = "demo"  # demo | benchmark | pilot | approved_study

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
