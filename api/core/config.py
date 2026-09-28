from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    DATABASE_URL: str
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    STORAGE_TYPE: str = "supabase"
    LOCAL_STORAGE_PATH: str = "storage"
    SECRET_KEY: str = ""
    JWT_SECRET_KEY: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    REDIRECT_URI: str = ""
    API_URL: str
    CLIENT_URL: str
    FEATURE_SELECTION_MODEL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", secrets_dir="/run/secrets", extra="ignore"
    )

    @model_validator(mode="after")
    def sync_secret_keys(self):
        if not self.JWT_SECRET_KEY and self.SECRET_KEY:
            self.JWT_SECRET_KEY = self.SECRET_KEY
        if not self.SECRET_KEY and self.JWT_SECRET_KEY:
            self.SECRET_KEY = self.JWT_SECRET_KEY
        return self


settings = Settings()
