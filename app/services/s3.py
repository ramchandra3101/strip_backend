import boto3
import logging
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
import os
from core.config import settings
from core.exceptions import StorageError
from botocore.config import Config
import mimetypes

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        "Initializing s3 services with retries and timeouts"
        self.config = Config(
            retries = dict(
                max_attempts = 3,
                mode = 'adaptive'
            ),
            connect_timeout = 5,
            read_timeout = 10 
        )

        try:
            self.client = boto3.client(
                's3',
                aws_access_key_id = settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key = settings.AWS_SECRET_ACCESS_KEY,
                region_name = settings.AWS_REGION,
                config = self.config
            )
            self.bucket_name = settings.S3_BUCKET
            if not settings.DEV_MODE:
                self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                logger.error(f"Bucket {self.bucket_name} does not exist")
                raise StorageError(f"Bucket {self.bucket_name} does not exist")
            elif error_code == '403':
                logger.error(f"Access denied to bucket {self.bucket_name}")
                raise StorageError(f"Access denied to bucket {self.bucket_name}")
            else:
                logger.error(f"Failed to Initialize S3 client: {str(e)}")
                raise StorageError(f"Storage Initialization Failed: {str(e)}")
            
        except Exception as e:
            if settings.DEV_MODE:
                logger.warning(f"running in Dev mode without s3 access: {str(e)}")
            else:
                logger.error(f"Failed to Initialize S3 client: {str(e)}")
                raise StorageError(f"Storage Initialization Failed: {str(e)}")
            
    def create_folder(self, folder_name: str) -> str:
        "Creating folder (prefix) in s3 bucket"
        try:
            folder_name = folder_name.rstrip('/')+'/'
            self.client.put_object(Bucket=self.bucket_name, Key=folder_name)
            logger.info(f"Created folder {folder_name} in bucket {self.bucket_name}")
            return folder_name
        except ClientError as e:
            logger.error(f"Failed to create folder {folder_name}: {str(e)}")
            raise StorageError(f"Failed to create folder {folder_name}: {str(e)}")
        
    def upload_file(self, file_path: str, s3_key:str,content_type: Optional[str]= None) -> str:
        "Upload file to s3 bucket"
        try:
            if content_type is None:
                content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
            with open(file_path, 'rb') as file:
                self.client.upload_fileobj(file, self.bucket_name, s3_key, ExtraArgs={'ContentType': content_type })
                file_url = self.generate_url(s3_key)
                logger.info(f"Uploaded file to {file_url}")
                return file_url
        except ClientError as e:
            logger.error(f"Failed to upload file {file_path} to s3: {str(e)}")
            raise StorageError(f"Failed to upload file {file_path} to s3: {str(e)}")
        except IOError as e:
            logger.error(f"Failed to read file {file_path}: {str(e)}")
            raise StorageError(f"Failed to read file {file_path}: {str(e)}")
    def upload_fileobj(self, file_onj:BinaryIO, s3_key:str, content_type: Optional[str]= None) -> str:
        "Upload a file-like object to S3"
        try:
            if content_type is None:
                content_type = 'application/octet-stream'
            self.client.upload_fileobj(file_onj, self.bucket_name, s3_key, ExtraArgs={'ContentType': content_type})
            file_url = self.generate_url(s3_key)
            logger.info(f"Uploaded file object to {file_url}")
            return file_url
        except ClientError as e:
            logger.error(f"Failed to upload file object to s3: {str(e)}")
            raise StorageError(f"Failed to upload file object to s3: {str(e)}")
    def generate_url(self, file_key:str) -> str:
        "Generate public url for s3 object"
        return f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{file_key}"
    def delete_file(self, file_key:str)->None:
        "Delete file from s3 bucket"
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=file_key)
            files =[]
            for obj in response.get('Contents', []):
                files.append({'Key': obj['Key'],
                            'size': obj['Size'],
                            'LastModified': obj['LastModified'].isoformat(),
                            'url': self.generate_url(obj['Key'])
                            })
            return files
        except ClientError as e:
            logger.error(f"Failed to list objects in {file_key}: {str(e)}")
            raise StorageError(f"Failed to list objects in {file_key}: {str(e)}")
                
                              

    



    

