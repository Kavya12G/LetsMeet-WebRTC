from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    ALLOWED_ORIGINS: List[str] = ["*"]
    TURN_URL: str = "turn:openrelay.metered.ca:80"
    TURN_USERNAME: str = "openrelayproject"
    TURN_CREDENTIAL: str = "openrelayproject"

    class Config:
        env_file = ".env"

settings = Settings()
