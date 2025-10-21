from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "QA Chatbot API"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # API Configuration
    api_v1_prefix: str = "/api/v1"
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: str = Field(default="", description="Redis password")
    
    # CORS Configuration
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()