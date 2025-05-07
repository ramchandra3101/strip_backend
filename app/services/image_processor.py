# app/services/image_processor.py
import os
import json
import logging
from fastapi import UploadFile
from typing import Optional, Dict
from .image_utils import ImageUtils
from .s3 import S3Service
from core.config import settings
from core.exceptions import ImageProcessingError
from services.removebg import handle_image_processing



logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, base_path: str = settings.TEMP_DIR):
        """Initialize image processor with base path"""
        self.base_path = base_path
        self.utils = ImageUtils()
        self.s3 = S3Service()
        if not os.path.exists(base_path):
            os.makedirs(base_path)

    def create_local_folder(self, input_file_name: str) -> str:
        """Create a folder for the current processing job"""
        folder_name = os.path.splitext(input_file_name)[0]
        folder_path = os.path.join(self.base_path, folder_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        return folder_path

    async def process_image(self, file: UploadFile) -> Dict:
        """
        Process the uploaded image through the complete pipeline
        """
        try:
            # Create local folder and save uploaded file
            input_file_name = file.filename
            local_folder_path = self.create_local_folder(input_file_name)
            local_input_path = os.path.join(local_folder_path, input_file_name)

            # Save the uploaded file
            content = await file.read()
            with open(local_input_path, "wb") as buffer:
                buffer.write(content)

            try:
              
                removed_bg_path =  handle_image_processing(local_input_path)

              
                straightened_image, processed_path = self.utils.process_image(removed_bg_path)

                if straightened_image is None:
                    raise ImageProcessingError("Failed to process image")

                # Step 3: Crop and analyze
                
                cropped_image, cropped_path = self.utils.crop_and_display(
                    straightened_image, 
                    processed_path
                )

                # Step 4: Generate plot and analyze intensities
                plot_path, control_line, test_line = self.utils.convert_to_bw_and_plot(
                    cropped_image,
                    local_folder_path
                )

                # Create S3 folder
                folder_name = self.s3.create_folder(input_file_name)

                # Upload all files
                files_to_upload = {
                    'Original': local_input_path,
                    'removedbg': removed_bg_path,
                    'processed': processed_path,
                    'cropped': cropped_path,
                    'plot': plot_path
                }

                urls = {}
                for key, path in files_to_upload.items():
                    s3_key = f"{folder_name}{os.path.basename(path)}"
                    self.s3.upload_file(path, s3_key)
                    urls[key] = self.s3.generate_url(s3_key)


                # Return results
                return {
                    "Status": "200 OK",
                    "message": "Image processed successfully",
                    "bucket_name": self.s3.bucket_name,
                    "folder_name": folder_name,
                    "urls": urls,
                    "intensity": {
                        "controlLine": float(control_line),
                        "testLine": float(test_line)
                    }
                }

            finally:
                # Cleanup temporary files
                self._cleanup_files([
                    local_input_path,
                    removed_bg_path if 'removed_bg_path' in locals() else None,
                    processed_path if 'processed_path' in locals() else None,
                    cropped_path if 'cropped_path' in locals() else None,
                    plot_path if 'plot_path' in locals() else None
                ])

        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise ImageProcessingError(str(e))

    def _cleanup_files(self, file_paths: list):
        """Clean up temporary files"""
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {str(e)}")

    def __del__(self):
        """Cleanup when the processor is destroyed"""
        try:
            if os.path.exists(self.base_path):
                for item in os.listdir(self.base_path):
                    item_path = os.path.join(self.base_path, item)
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            import shutil
                            shutil.rmtree(item_path)
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {item_path}: {str(e)}")
        except Exception as e:
            logger.warning(f"Failed to cleanup base directory: {str(e)}")