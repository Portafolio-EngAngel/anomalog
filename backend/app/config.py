from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://anomalog:anomalog@localhost:5432/anomalog"
    anthropic_api_key: str

    model_config = {"env_file": ".env"}


settings = Settings()
