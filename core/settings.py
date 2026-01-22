from pydantic import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    app_name: str = "RAG Dashboard"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    host: str = "0.0.0.0"
    port: int = 8000

    firebase_project_id: str = ""
    firebase_private_key: str = ""
    firebase_client_email: str = ""
    firebase_api_key: str = ""
    firebase_auth_domain: str = ""
    firebase_storage_bucket: str = ""
    firebase_messaging_sender_id: str = ""
    firebase_app_id: str = ""

    firebase_type: str = "service_account"
    firebase_private_key_id: str = ""
    firebase_auth_provider_x509_cert_url: str = "https://www.googleapis.com/oauth2/v1/certs"
    firebase_client_x509_cert_url: str = ""

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    allowed_origins_str: str = "http://localhost:3000,http://localhost:8000"

    database_url: str = ""

    @property
    def allowed_origins(self) -> List[str]:
        """Parse comma-separated origins string into list"""
        return [origin.strip() for origin in self.allowed_origins_str.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()