from fastapi import APIRouter
from core.config import settings
from core.exceptions import ValidationError

router = APIRouter()
@router.get("/health")
async def health_check():
    return {
        "status": "Healthy", 
        "version": settings.API_VERSION,
        "mode": "Development" if settings.DEBUG else "Production",
        "aws_configured": settings.is_aws_configured
    }

@router.get("/error")
async def test_error():
    raise ValidationError("This is a test error")