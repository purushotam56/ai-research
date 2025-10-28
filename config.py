import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration settings that can be used throughout the application

# API Configuration
IBM_API_KEY: Optional[str] = os.getenv("IBM_API_KEY", "your-api-key-here")
IBM_PROJECT_ID: Optional[str] = os.getenv("IBM_PROJECT_ID", "your-project-id-here")
IBM_URL: str = os.getenv("IBM_URL", "https://api.example.com")

# Additional configuration options
DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
PORT: int = int(os.getenv("PORT", "8000"))

# Validate required configuration
def validate_config() -> bool:
    """Validate that required configuration values are set."""
    required_configs = {
        "IBM_API_KEY": IBM_API_KEY,
        "IBM_PROJECT_ID": IBM_PROJECT_ID,
        "IBM_URL": IBM_URL
    }
    
    missing_configs = [key for key, value in required_configs.items() if not value or value.startswith("your-")]
    
    if missing_configs:
        print(f"Warning: Missing or default configuration values: {', '.join(missing_configs)}")
        return False
    
    return True

# Export all configuration variables
__all__ = [
    "IBM_API_KEY",
    "IBM_PROJECT_ID", 
    "IBM_URL",
    "DEBUG",
    "PORT",
    "validate_config"
]