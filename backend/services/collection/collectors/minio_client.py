from minio import Minio
from minio.error import S3Error
from django.conf import settings
import io
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MinIOClient:
    """
    MinIO client for storing collection data locally
    """

    def __init__(self):
        self.client = Minio(
            getattr(settings, "MINIO_ENDPOINT", "localhost:9000"),
            access_key=getattr(settings, "MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=getattr(settings, "MINIO_SECRET_KEY", "minioadmin"),
            secure=getattr(settings, "MINIO_SECURE", False),
        )
        self.bucket_name = getattr(settings, "MINIO_BUCKET", "revmine-collections")
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created MinIO bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket exists: {e}")

    def generate_filename(
        self, repository_name: str, collection_id: int, file_type: str = "json"
    ) -> str:
        """
        Generate filename with structure: projectname_collectionid_timestamp.ext
        Example: my-project_123_20231201_143022.json
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_repo_name = repository_name.replace("/", "_").replace(" ", "_").lower()
        return f"{clean_repo_name}_collection{collection_id}_{timestamp}.{file_type}"

    def save_json(self, data: dict, filename: str) -> bool:
        """Save JSON data to MinIO"""
        try:
            json_bytes = json.dumps(data, indent=2).encode("utf-8")
            json_stream = io.BytesIO(json_bytes)

            self.client.put_object(
                self.bucket_name,
                filename,
                json_stream,
                length=len(json_bytes),
                content_type="application/json",
            )

            logger.info(f"Successfully saved {filename} to MinIO")
            return True
        except S3Error as e:
            logger.error(f"Error saving to MinIO: {e}")
            return False

    def get_json(self, filename: str) -> dict:
        """Retrieve JSON data from MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, filename)
            data = json.loads(response.read().decode("utf-8"))
            return data
        except S3Error as e:
            logger.error(f"Error retrieving from MinIO: {e}")
            return None
        finally:
            if response:
                response.close()
                response.release_conn()
    
    def get_json_bytes(self, filename: str) -> bytes:
        """Retrieve JSON data from MinIO as raw bytes (for streaming downloads)"""
        response = None
        try:
            response = self.client.get_object(self.bucket_name, filename)
            data = response.read()
            return data
        except S3Error as e:
            logger.error(f"Error retrieving JSON bytes from MinIO: {e}")
            return None
        finally:
            if response:
                response.close()
                response.release_conn()
    
    def save_csv(self, csv_content: str, filename: str) -> bool:
        """Save CSV data to MinIO"""
        try:
            csv_bytes = csv_content.encode("utf-8")
            csv_stream = io.BytesIO(csv_bytes)

            self.client.put_object(
                self.bucket_name,
                filename,
                csv_stream,
                length=len(csv_bytes),
                content_type="text/csv",
            )

            logger.info(f"Successfully saved {filename} to MinIO")
            return True
        except S3Error as e:
            logger.error(f"Error saving CSV to MinIO: {e}")
            return False

    def get_csv(self, filename: str) -> str:
        """Retrieve CSV data from MinIO as string"""
        response = None
        try:
            response = self.client.get_object(self.bucket_name, filename)
            data = response.read().decode("utf-8")
            return data
        except S3Error as e:
            logger.error(f"Error retrieving CSV from MinIO: {e}")
            return None
        finally:
            if response:
                response.close()
                response.release_conn()

    def get_csv_bytes(self, filename: str) -> bytes:
        """Retrieve CSV data from MinIO as raw bytes (preserves exact content)"""
        response = None
        try:
            response = self.client.get_object(self.bucket_name, filename)
            data = response.read()
            return data
        except S3Error as e:
            logger.error(f"Error retrieving CSV bytes from MinIO: {e}")
            return None
        finally:
            if response:
                response.close()
                response.release_conn()

    def file_exists(self, filename: str) -> bool:
        """Check if file exists in MinIO"""
        try:
            self.client.stat_object(self.bucket_name, filename)
            return True
        except S3Error:
            return False
    
    def save_stream(self, file_stream, filename: str, length: int, content_type: str = 'application/json') -> bool:
        """Stream a file directly to MinIO without loading the full content into memory."""
        try:
            self.client.put_object(
                self.bucket_name,
                filename,
                file_stream,
                length=length,
                content_type=content_type,
            )
            logger.info(f"Successfully streamed {filename} ({length} bytes) to MinIO")
            return True
        except S3Error as e:
            logger.error(f"Error streaming to MinIO: {e}")
            return False

    def get_object_stream(self, filename: str):
        """Get a streaming response from MinIO. Caller must close and release."""
        try:
            return self.client.get_object(self.bucket_name, filename)
        except S3Error as e:
            logger.error(f"Error getting stream from MinIO: {e}")
            return None

    def delete_file(self, filename: str) -> bool:
        """Delete file from MinIO"""
        try:
            self.client.remove_object(self.bucket_name, filename)
            logger.info(f"Deleted {filename} from MinIO")
            return True
        except S3Error as e:
            logger.error(f"Error deleting from MinIO: {e}")
            return False
