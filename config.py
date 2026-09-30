from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    secret_key: str = "local-development-key-change-before-deployment"
    database_path: str = "./data/pocketsmart.db"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    cookie_secure: bool = False
    allowed_origins: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()