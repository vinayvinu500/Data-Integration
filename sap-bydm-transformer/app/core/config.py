from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    # API settings
    APP_NAME: str = "SAP-BYDM-Transformer"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # MinIO settings
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "data"
    
    # File paths
    MAPPINGS_FOLDER: str = Field(default="mappings", alias="MAPPING_FOLDER")  # Added alias
    TEMPLATE_FOLDER: str = "templates"
    SOURCE_FOLDER: str = "source"
    TARGET_FOLDER: str = "target"
    LOG_FOLDER: str = "logs"
    
    # Processing settings
    BATCH_SIZE: int = 100
    MAX_WORKERS: int = 4
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",  # Ignore extra fields
        "populate_by_name": True  # Allow populating by field name or alias
    }

# Create settings instance
settings = Settings()

# Function to validate essential configuration
def validate_config():
    """Validates that essential configuration variables are set."""
    essential_vars = {
        "MINIO_ENDPOINT": settings.MINIO_ENDPOINT,
        "MINIO_ACCESS_KEY": settings.MINIO_ACCESS_KEY,
        "MINIO_SECRET_KEY": settings.MINIO_SECRET_KEY,
        "MINIO_BUCKET": settings.MINIO_BUCKET,
    }
    
    missing_vars = [key for key, value in essential_vars.items() if not value]
    if missing_vars:
        raise ValueError(f"Missing essential configuration variables: {', '.join(missing_vars)}")
    
    return True