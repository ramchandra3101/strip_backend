from pydantic_settings import BaseSettings
from typing import List
import secrets
import os
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):

    #API settings
    API_VERSION : str = "v1"
    PROJECT_NAME : str = "Striplens_API"
    DEBUG : bool = False

    #Security
    SECRET_KEY : str = secrets.token_urlsafe(32)

    #CORS
    CORS_ORIGINS : List[str] = ["*"]

    #AWS S3
    AWS_ACCESS_KEY_ID : str
    AWS_SECRET_ACCESS_KEY : str
    AWS_REGION : str
    S3_BUCKET : str = "striplensapp"

    DEV_MODE: bool = True

    #Image_processing settings
    MAX_IMAGE_SIZE : int = 10 * 1024 * 1024 #10MB
    ALLOWED_IMAGE_TYPES : List[str] = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    TEMP_DIR : str 

    #Rate limiting
    RATE_LIMIT_PER_MINUTE : int = 10

    class Config:
        env_file = "app/.env"
        case_sensitive = True

    @property
    def is_aws_configured(self):
        """CheckING if AWS credentials are properly configured"""
        return all([self.AWS_ACCESS_KEY_ID, self.AWS_SECRET_ACCESS_KEY, self.AWS_REGION])

settings = Settings() #creating instance

os.makedirs(settings.TEMP_DIR, exist_ok=True) #creating temp directory

if settings.DEV_MODE:
    print("⚠️ Running in DEVELOPMENT mode")
    if not settings.is_aws_configured:
        print("⚠️ AWS credentials are not configured. Please set them in .env file")
    


