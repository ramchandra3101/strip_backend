from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from core.exceptions import StripLensException
from core.config import settings
import logging
import time
import traceback


from api.endpoints import health, image


logging.basicConfig(
    level = logging.INFO if not settings.DEBUG else logging.DEBUG,
    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

#Initializing FastAPI app
app = FastAPI(
    title = settings.PROJECT_NAME,
    version = settings.API_VERSION,
    debug = settings.DEBUG
)
#CORS middleware
app.add_middleware (
    CORSMiddleware,
    allow_origins = settings.CORS_ORIGINS,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)
#Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time =time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"Method: {request.method} Path: {request.url.path}"
        f"Status: {response.status_code} Duration: {duration:.2f}s" 
    )
    return response

#Global exception Handlers

@app.exception_handler(StripLensException)
async def striplens_exception_handlers(request: Request, exc: StripLensException):
    return JSONResponse(
        status_code = exc.status_code,
        content = {
            "error": exc.detail,
            "type":exc.__class__.__name__
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code = 500,
        content = {
            "error": "Internal server error",
            "type": "InternalError",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

app.include_router(health.router, tags=["health"])
app.include_router(image.router, prefix="/image", tags=["image"])



if __name__ == "__main__":
    import uvicorn
    if settings.DEV_MODE:
        logger.info("Starting development server...")
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=8000, 
            reload=True,
            log_level="debug" if settings.DEBUG else "info"
        )
    else:
        # Production server configuration
        uvicorn.run(
            "main:app", 
            host="0.0.0.0", 
            port=8000, 
            workers=4,
            log_level="info"
        )
        