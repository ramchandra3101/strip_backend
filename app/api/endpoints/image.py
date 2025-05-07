from fastapi import APIRouter, File, UploadFile, Query
from services.image_processor import ImageProcessor
from services.s3 import S3Service
from core.exceptions import ValidationError, StorageError, ImageProcessingError
from core.config import settings
import logging
import tempfile
import os

logger = logging.getLogger(__name__)
router = APIRouter()
s3_service = S3Service()
image_processor = ImageProcessor()

@router.post("/upload-test")
async def upload_test(file: UploadFile = File(...)):
    """Testing endpoint for s3 uploads"""
    try:
        temp_file_path = ""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
        
        s3_key = f"test-uploads/{file.filename}"
        file_url = s3_service.upload_file(temp_file_path, s3_key, content_type=file.content_type)
        
        os.unlink(temp_file_path)
        
        return {
            "status": "200 OK",
            "message": "File uploaded successfully",
            "file_url": file_url
        }
    except Exception as e:
        logger.error(f"Upload test failed: {str(e)}")
        if temp_file_path:
            try:
                os.unlink(temp_file_path)
            except OSError as cleanup_error:
                logger.error(f"Failed to delete temp file: {str(cleanup_error)}")
        raise StorageError(f"Upload test failed: {str(e)}")

@router.post("/test/upload")
async def test_upload(file: UploadFile = File(...)):
    """Testing endpoint for s3 uploads with validation"""
    temp_file_path = ""
    try:
        if not file.filename:
            raise ValidationError("No file name provided")
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"Invalid file type. Allowed types: {settings.ALLOWED_IMAGE_TYPES}")
        
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()

            if len(content) > settings.MAX_IMAGE_SIZE:
                raise ValidationError(f"File size exceeds the limit of {settings.MAX_IMAGE_SIZE} bytes")
            temp_file.write(content)
            temp_file.flush()
        
        s3_key = f"test-uploads/{file.filename}"
        file_url = s3_service.upload_file(temp_file_path, s3_key, content_type=file.content_type)
        return {
            "status": "200 OK",
            "message": "File uploaded successfully",
            "file_url": file_url
        }
    except Exception as e:
        logger.error(f"Upload test failed: {str(e)}")
        raise StorageError(f"Upload test failed: {str(e)}")

@router.post("/process")
async def test_process(file: UploadFile = File(...),
                       client_id: str = Query(None, description="WebSocket client ID for progress updates")):
    """Test endpoint for image processing without WebSocket"""
    try:
        if not file.filename:
            raise ValidationError("No file provided")

        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"Invalid file type. Allowed types: {settings.ALLOWED_IMAGE_TYPES}")

        result = await image_processor.process_image(file)
        return result

    except Exception as e:
        logger.error(f"Process test failed: {str(e)}")
        raise ImageProcessingError(f"Failed to process image: {str(e)}")
    
