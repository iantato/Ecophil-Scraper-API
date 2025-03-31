from typing import Dict
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class IntercommerceURLs(BaseSettings):
    """Intercommerce URLs for different company branches."""

    MAIN_BRANCH: str
    FCIE_BRANCH: str

    model_config = SettingsConfigDict(
        env_file='.env',
        env_prefix='URL_',
        env_file_encoding='utf-8',
        extra='ignore'
    )

class Settings(BaseSettings):
    """Load environment variables from a .env file."""

    # Different Intercommerce URLs for different company branches.
    INTERCOMMERCE_URLS: Dict[str, str] = IntercommerceURLs().model_dump()

    # Intercommerce Credentials.
    INTERCOMMERCE_USERNAME: str
    INTERCOMMERCE_PASSWORD: SecretStr

    # VBS Credentials.
    VBS_USERNAME: str
    VBS_PASSWORD: SecretStr

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra = 'ignore'
    )