"""Application configuration using Pydantic settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    llm_base_url: str = "https://model-router.meitu.com/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen-turbo"
    # Default vision model to the same as llm_model, because on this router
    # `qwen-turbo` can accept base64 images via chat.completions (per provided docs).
    llm_vision_model: str = "qwen-turbo"

    # Image Model Configuration (SD API style)
    image_model_endpoint: str = ""

    # MHC Image-to-Image API Configuration (test_minimal 方式: runAsync + queryResult)
    mhc_app: str = "mhc"
    mhc_biz: str = "mhc_proj_xxx"
    mhc_region: str = "pre-meitu"
    mhc_env: str = "outer"
    mhc_api_path: str = "v1/outsourcing_gateway_submit_async"
    # 外采改图/生图权限 Token（联系元建获取），parameter.token 必填
    mhc_nano_token: str = ""

    # Application Settings
    max_image_size: int = 10485760  # 10MB
    storage_path: str = "./storage"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
