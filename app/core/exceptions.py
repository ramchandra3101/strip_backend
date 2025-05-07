from fastapi import HTTPException, status
from typing import Any, Dict, Optional
class StripLensException(HTTPException): #Base Exception
    def __init__(self, status_code: int, detail: str, headers: Optional[Dict[str, Any]] = None):
        super().__init__(status_code, detail=detail, headers=headers)

class ImageProcessingError(StripLensException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

class StorageError(StripLensException):
    def __init__(self, detail: str):
        super().__init__(status_code = status. HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class ValidationError(StripLensException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class WebSocketError(StripLensException):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
    

