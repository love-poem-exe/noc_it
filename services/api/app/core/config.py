from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "noc-it-backend"
    api_prefix: str = "/api"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
