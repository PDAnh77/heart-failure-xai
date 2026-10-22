from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    FILE_STORAGE_PROVIDER: str = "local"
    LOCAL_STORAGE_PATH: str = "storage"
    JWT_SECRET_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    REDIRECT_URI: str = ""
    API_URL: str
    CLIENT_URL: str

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", secrets_dir="/run/secrets", extra="ignore"
    )


settings = Settings()
