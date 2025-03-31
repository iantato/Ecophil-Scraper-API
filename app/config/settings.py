from typing import Dict
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class IntercommerceURLs(BaseSettings):
    """Intercommerce URLs for different company branches."""

    MAIN_BRANCH: str = Field(alias='main', validation_alias='URL_MAIN_BRANCH')
    FCIE_BRANCH: str = Field(alias='fcie', validation_alias='URL_FCIE_BRANCH')

    model_config = SettingsConfigDict(
        env_file='.env',
        env_prefix='URL_',
        env_file_encoding='utf-8',
        extra='ignore'
    )

class Settings(BaseSettings):
    """Load environment variables from a .env file."""

    # Different Intercommerce URLs for different company branches.
    INTERCOMMERCE_URLS: Dict[str, str] = IntercommerceURLs().model_dump(by_alias=True)

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