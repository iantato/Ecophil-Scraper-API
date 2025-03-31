from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Load environment variables from a .env file."""

    # Different Intercommerce URLs for different company branches.
    MAIN_BRANCH_URL: str
    FCIE_BRANCH_URL: str

    # Intercommerce Credentials.
    INTERCOMMERCE_USERNAME: str
    INTERCOMMERCE_PASSWORD: SecretStr

    # VBS Credentials.
    VBS_USERNAME: str
    VBS_PASSWORD: SecretStr

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8'
    )