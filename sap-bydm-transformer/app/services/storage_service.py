from io import BytesIO
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger("app")

class StorageService:
    """Service for interacting with MinIO object storage."""
    
    def __init__(self):
        """Initialize MinIO client with configuration from settings."""
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create the bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(settings.MINIO_BUCKET):
                self.client.make_bucket(settings.MINIO_BUCKET)
                logger.info(f"Created bucket: {settings.MINIO_BUCKET}")
            else:
                logger.info(f"Bucket already exists: {settings.MINIO_BUCKET}")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
            raise
    
    def list_files(self, prefix: str = "") -> List[str]:
        """
        List all files with a given prefix.
        
        Args:
            prefix: The prefix to filter objects (like a folder path)
            
        Returns:
            List of object names matching the prefix
        """
        try:
            objects = self.client.list_objects(settings.MINIO_BUCKET, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Failed to list files with prefix '{prefix}': {e}")
            raise Exception(f"Failed to list files: {e}")
    
    def load_file(self, file_path: str) -> bytes:
        """
        Load file content from MinIO.
        
        Args:
            file_path: Path to the file within the bucket
            
        Returns:
            File content as bytes
        """
        try:
            response = self.client.get_object(settings.MINIO_BUCKET, file_path)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Failed to load file '{file_path}': {e}")
            raise Exception(f"Failed to load file {file_path}: {e}")
    
    def load_json(self, file_path: str) -> Dict[str, Any]:
        """
        Load and parse JSON file from MinIO.
        
        Args:
            file_path: Path to the JSON file within the bucket
            
        Returns:
            Parsed JSON as dictionary
        """
        content = self.load_file(file_path)
        return json.loads(content)
    
    def save_file(self, data: bytes, file_path: str, content_type: str = "application/octet-stream") -> str:
        """
        Save binary data to MinIO.
        
        Args:
            data: Binary data to save
            file_path: Path where to save the file
            content_type: MIME type of the content
            
        Returns:
            Path to the saved file
        """
        try:
            data_stream = BytesIO(data)
            
            self.client.put_object(
                settings.MINIO_BUCKET,
                file_path,
                data_stream,
                length=len(data),
                content_type=content_type
            )
            
            logger.info(f"Saved file to {file_path}")
            return file_path
        except S3Error as e:
            logger.error(f"Failed to save file to '{file_path}': {e}")
            raise Exception(f"Failed to save file to {file_path}: {e}")
    
    def save_json(self, data: Dict[str, Any], file_path: str) -> str:
        """
        Save JSON data to MinIO.
        
        Args:
            data: Dictionary to save as JSON
            file_path: Path where to save the JSON file
            
        Returns:
            Path to the saved JSON file
        """
        json_data = json.dumps(data, indent=2).encode("utf-8")
        return self.save_file(json_data, file_path, content_type="application/json")
    
    def save_log(self, log_content: str) -> str:
        """
        Save log file to MinIO.
        
        Args:
            log_content: Log content as string
            
        Returns:
            Path to the saved log file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"{settings.LOG_FOLDER}/transform_{timestamp}.log"
        
        log_data = log_content.encode("utf-8")
        return self.save_file(log_data, log_path, content_type="text/plain")