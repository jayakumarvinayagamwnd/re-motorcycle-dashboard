from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Motorcycle Dashboard API"
    app_version: str = "0.1.0"

    # Camera stream URLs (camera 1 = front, camera 2 = rear)
    camera_1_url: str = "http://192.168.1.5/camera/stream"
    camera_2_url: str = "http://192.168.1.6/camera/stream"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()