# config.py - Configuration management
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    app_name: str = "FastAPI Celery Socket.IO"
    debug: bool = False
    
    # Celery settings
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Socket.IO settings
    socketio_cors_origins: list = ["*"]
    
    class Config:
        env_file = ".env"

settings = Settings()