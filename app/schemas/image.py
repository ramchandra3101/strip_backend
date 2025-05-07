# app/schemas/image.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Dict, Optional
from enum import Enum

class ImageStatus(str, Enum):
    """Status of image processing"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class UploadResponse(BaseModel):
    """Response model for file uploads"""
    status: str = Field(..., example="200 OK")
    message: str = Field(..., example="File uploaded successfully")
    file_url: HttpUrl = Field(..., example="https://bucket.s3.region.amazonaws.com/file.jpg")

class IntensityResults(BaseModel):
    """Model for intensity measurement results"""
    controlLine: float = Field(..., example=0.85)
    testLine: float = Field(..., example=0.65)

class ProcessingResponse(BaseModel):
    """Response model for image processing"""
    Status: str = Field(..., example="200 OK")
    message: str = Field(..., example="Image processed successfully")
    bucket_name: str = Field(..., example="striplens")
    folder_name: str = Field(..., example="test_image/")
    urls: Dict[str, HttpUrl] = Field(..., example={
        "removedbg": "https://bucket.s3.region.amazonaws.com/no_bg.png",
        "processed": "https://bucket.s3.region.amazonaws.com/processed.png",
        "cropped": "https://bucket.s3.region.amazonaws.com/cropped.png",
        "plot": "https://bucket.s3.region.amazonaws.com/plot.png"
    })
    intensity: IntensityResults

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., example="Failed to process image")
    type: str = Field(..., example="ImageProcessingError")
    detail: Optional[str] = Field(None, example="Could not detect test lines")

class WebSocketMessage(BaseModel):
    """Base model for WebSocket messages"""
    type: str = Field(..., example="status_update")
    data: str = Field(..., example="Processing image...")

class ProcessingProgress(BaseModel):
    """Model for processing progress updates"""
    status: ImageStatus
    progress: int = Field(..., ge=0, le=100, example=75)
    message: str = Field(..., example="Removing background...")
    detail: Optional[str] = None