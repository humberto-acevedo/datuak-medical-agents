"""Configuration management for the medical record analysis system."""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class AWSConfig:
    """AWS configuration settings."""
    region: str
    access_key_id: Optional[str]
    secret_access_key: Optional[str]
    account_id: str
    s3_bucket: str
    s3_endpoint_url: Optional[str] = None  # For LocalStack testing


@dataclass
class AppConfig:
    """Application configuration settings."""
    log_level: str
    environment: str
    research_api_timeout: int


@dataclass
class Config:
    """Main configuration class."""
    aws: AWSConfig
    app: AppConfig


def load_config() -> Config:
    """Load configuration from environment variables."""
    
    # Validate required AWS settings
    region = os.getenv("AWS_REGION", "us-east-1")
    if region != "us-east-1":
        raise ValueError("AWS_REGION must be 'us-east-1' for HIPAA compliance")
    
    aws_config = AWSConfig(
        region=region,
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        account_id=os.getenv("AWS_ACCOUNT_ID", "539247495490"),
        s3_bucket=os.getenv("S3_BUCKET", "patient-records-20251024"),
        s3_endpoint_url=os.getenv("S3_ENDPOINT_URL")  # For LocalStack
    )
    
    app_config = AppConfig(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        environment=os.getenv("ENVIRONMENT", "development"),
        research_api_timeout=int(os.getenv("RESEARCH_API_TIMEOUT", "30"))
    )
    
    return Config(aws=aws_config, app=app_config)


# Global configuration instance
config = load_config()

def get_config() -> Config:
    """Get the global configuration instance."""
    return config