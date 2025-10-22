from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    name: str = "QA Chatbot API"
    version: str = "1.0.0"
    debug: bool = False
    prefix: str = "/api/v1"
    allowed_origins: list = ["*"]


settings = Settings()
