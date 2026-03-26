from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    TURN_URL: str = "turn:openrelay.metered.ca:80"
    TURN_USERNAME: str = "openrelayproject"
    TURN_CREDENTIAL: str = "openrelayproject"

    class Config:
        env_file = ".env"

settings = Settings()