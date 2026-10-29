from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "IMAGINA"
    app_version: str = "0.5.0.dev1"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    allowed_hosts: str = "127.0.0.1,localhost,testserver,test,backend"
    database_url: str = "sqlite+aiosqlite:///./data/imagina.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    max_session_duration_seconds: int = 1200  # 20 minutes
    window_interval_seconds: float = 2.0
    enable_experimental_lsl: bool = False
    study_mode: str = "demo"  # demo | benchmark | pilot | approved_study
    imagine_enable_remote_diffusion: bool = False
    imagine_diffusion_url: str = ""
    imagine_diffusion_token: str = ""
    imagine_diffusion_timeout_seconds: int = 180
    imagine_asset_ttl_hours: int = 24
    imagine_data_dir: str = "./data/imagine"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
