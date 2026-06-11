import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Kiosk Billing & Cash POS"
    API_PREFIX: str = "/api"
    
    # Path to SQLite database file
    DB_PATH: str = "kiosco.db"
    
    # Root directory of the project
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # JWT security settings
    JWT_SECRET_KEY: str = "super-secret-key-change-in-production-kiosco-pos-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Default Admin credentials
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    
    # Absolute path to schema.sql
    @property
    def SCHEMA_PATH(self) -> str:
        return os.path.join(self.BASE_DIR, "database", "schema.sql")

    # Absolute path to SQLite database
    @property
    def DB_URL(self) -> str:
        # If DB_PATH is relative, place it in the project root directory
        if not os.path.isabs(self.DB_PATH):
            return os.path.join(self.BASE_DIR, self.DB_PATH)
        return self.DB_PATH

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
