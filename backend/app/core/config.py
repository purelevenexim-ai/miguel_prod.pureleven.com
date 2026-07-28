from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str
    DATABASE_URL: str
    ENCRYPTION_KEY: str = ""

    # When enabled, confirmed orders will fail fast on insufficient stock.
    ENFORCE_STOCK_VALIDATION: bool = False
    INTERNAL_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

