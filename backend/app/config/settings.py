from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Motorcycle Dashboard API"
    app_version: str = "0.1.0"

    # Camera stream URLs (camera 1 = front, camera 2 = rear)
    camera_1_url: str = "http://192.168.1.8/camera/stream"
    camera_2_url: str = "http://192.168.1.6/camera/stream"

    # SQLite database path (relative to project root)
    database_path: str = "data/motorcycle.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def database_url(self) -> str:
        """Return the SQLite connection URL for SQLAlchemy-style usage."""
        return f"sqlite:///{self.database_path}"

    @property
    def database_file(self) -> Path:
        """Return the resolved database file path."""
        return Path(self.database_path).resolve()


settings = Settings()
