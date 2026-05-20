from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )

    secret_key: SecretStr

    database_url: str
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = ""

    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    otp_expire_minutes: int = 10

    mail_server: str = "localhost"
    mail_port: int = 587
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@sharafiai.com"
    mail_use_tls: bool = True

    ai_service_url: str = "http://localhost:8001/analyze"

settings = Settings()
