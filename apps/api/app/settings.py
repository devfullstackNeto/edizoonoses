from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://edi:edi@db:5432/edi"
    redis_url: str = "redis://redis:6379/0"
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "edi"
    s3_secret_key: str = "edi-demo-local-only"
    s3_bucket: str = "edi-documents"
    jwt_secret: str = "local-demo-change-before-network-exposure"
    demo_password: str = "Demo@2026"
    cors_origins: str = "http://localhost:5173,http://localhost:8090"
    demo_mode: bool = True
    osrm_base_url: str = ""
    ai_provider: str = "mock"
    ai_base_url: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    geocoder_base_url: str = ""
    geocoder_user_agent: str = "EDI-Zoonoses-Demo/1.0 (local technical pilot)"
    location_retention_days: int = 30
    geofence_radius_m: int = 100

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
