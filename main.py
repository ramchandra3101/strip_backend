from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Optional
import logging
import os
from removebg import handle_image_processing
from output import process_image, crop_and_display, convert_to_bw_and_plot
import boto3
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"Failed to connect websocket: {e}")
            raise

    async def _keep_alive(self, websocket: WebSocket):
        """Send periodic ping messages to keep the connection alive"""
        try:
            while websocket in self.active_connections:
                await asyncio.sleep(self.ping_interval)
                try:
                    await websocket.send_text("ping")
                except Exception:
                    await self.disconnect(websocket)
                    break
        except Exception as e:
            logger.error(f"Error in keep alive: {e}")
            await self.disconnect(websocket)

    async def disconnect(self, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
                logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def send_message(self, message: str, websocket: WebSocket):
        try:
            if websocket in self.active_connections:
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            await self.disconnect(websocket)

class S3Handler:
    def __init__(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.bucket_name = "striplens"

    def create_folder(self, input_file_name: str) -> str:
        folder_name = os.path.splitext(input_file_name)[0] + '/'
        self.client.put_object(Bucket=self.bucket_name, Key=folder_name)
        return folder_name

    def generate_url(self, file_key: str) -> str:
        return f"https://{self.bucket_name}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{file_key}"

    def upload_file(self, file_path: str, s3_key: str):
        try:
            self.client.upload_file(file_path, self.bucket_name, s3_key)
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise

class ImageProcessor:
    def __init__(self, base_path: str = '/tmp/striplens'):
        self.base_path = base_path
        if not os.path.exists(base_path):
            os.makedirs(base_path)

    def create_local_folder(self, input_file_name: str) -> str:
        folder_name = os.path.splitext(input_file_name)[0]
        folder_path = os.path.join(self.base_path, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path

    async def process_image(self, file: UploadFile, websocket: Optional[WebSocket] = None) -> dict:
        try:
            input_file_name = file.filename
            local_folder_path = self.create_local_folder(input_file_name)
            local_input_path = os.path.join(local_folder_path, input_file_name)

            # Save uploaded file
            with open(local_input_path, "wb") as buffer:
                buffer.write(await file.read())

            # Initialize S3 handler
            s3_handler = S3Handler()

            # Process image with status updates
            if websocket:
                await manager.send_message("Removing Background...", websocket)
            removed_bg_path = handle_image_processing(local_input_path)

            if websocket:
                await manager.send_message("Processing image...", websocket)
            straightened_image, processed_path = process_image(removed_bg_path)

            if straightened_image is None:
                raise HTTPException(status_code=422, detail="Failed to process image")

            if websocket:
                await manager.send_message("Creating plot...", websocket)
            cropped_image, cropped_path = crop_and_display(straightened_image, processed_path)
            plot_path, control_line, test_line = convert_to_bw_and_plot(cropped_image, local_folder_path)

            # Upload to S3
            folder_name = s3_handler.create_folder(input_file_name)
            files_to_upload = {
                'removedbg': removed_bg_path,
                'processed': processed_path,
                'cropped': cropped_path,
                'plot': plot_path
            }

            urls = {}
            for key, path in files_to_upload.items():
                s3_key = f"{folder_name}{os.path.basename(path)}"
                s3_handler.upload_file(path, s3_key)
                urls[key] = s3_handler.generate_url(s3_key)

            if websocket:
                await manager.send_message("Image processing complete!", websocket)

            return {
                "Status": "200 OK",
                "message": "Image processed successfully",
                "bucket_name": s3_handler.bucket_name,
                "folder_name": folder_name,
                "urls": urls,
                "intensity": {
                    "controlLine": control_line,
                    "testLine": test_line
                }
            }

        except Exception as e:
            logger.error(f"Error processing image: {e}")
            if websocket:
                await manager.send_message(f"Error: {str(e)}", websocket)
            raise HTTPException(status_code=500, detail=str(e))

# Initialize FastAPI app and managers
app = FastAPI()
manager = ConnectionManager()
image_processor = ImageProcessor()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/status")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await manager.connect(websocket)
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received message from client: {data}")
                if data == "init":
                    await manager.send_message("Connected", websocket)
            except WebSocketDisconnect:
                logger.info("Client disconnected normally")
                await manager.disconnect(websocket)
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await manager.disconnect(websocket)
                break
    except Exception as e:
        logger.error(f"Connection error: {e}")
        if websocket in manager.active_connections:
            await manager.disconnect(websocket)

@app.post("/processImage/")
async def process_file(file: UploadFile = File(...)):
    websocket = manager.active_connections[-1] if manager.active_connections else None
    return await image_processor.process_image(file, websocket)

