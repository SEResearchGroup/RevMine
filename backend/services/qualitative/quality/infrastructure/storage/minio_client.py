from minio import Minio
from minio.error import S3Error
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)


def _required_setting(name):
    value = getattr(settings, name, None)
    if not value:
        raise ImproperlyConfigured(f"{name} must be configured")
    return value


class MinIOClient:
    """Read-only MinIO access for the qualitative service.

    The collection service owns writing the raw + qualitative JSON; this service
    only ever reads the qualitative dataset back out of the shared bucket.
    """

    def __init__(self):
        self.client = Minio(
            _required_setting("MINIO_ENDPOINT"),
            access_key=_required_setting("MINIO_ACCESS_KEY"),
            secret_key=_required_setting("MINIO_SECRET_KEY"),
            secure=getattr(settings, "MINIO_SECURE", False) or False,
        )
        self.bucket_name = (
            getattr(settings, "MINIO_BUCKET_NAME", None)
            or getattr(settings, "MINIO_BUCKET", None)
            or "revmine-collections"
        )

    def get_json(self, filename: str) -> dict:
        """Retrieve and deserialize a JSON object from MinIO."""
        response = None
        try:
            response = self.client.get_object(self.bucket_name, filename)
            return json.loads(response.read().decode("utf-8"))
        except S3Error as e:
            logger.error(f"Error retrieving {filename} from MinIO: {e}")
            return None
        finally:
            if response:
                response.close()
                response.release_conn()

    def file_exists(self, filename: str) -> bool:
        try:
            self.client.stat_object(self.bucket_name, filename)
            return True
        except S3Error:
            return False
