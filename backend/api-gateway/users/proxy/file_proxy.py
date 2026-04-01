import logging
from django.http import HttpResponse

logger = logging.getLogger(__name__)


def detect_file_response(response, target_url):
    """
    DDetects if the response is a file to be downloaded.
    """
    content_type = response.headers.get("Content-Type", "")
    content_disposition = response.headers.get("Content-Disposition", "")

    # Detection by Content-Type
    if "text/csv" in content_type:
        return True

    # DDetection by Content-Disposition
    if "attachment" in content_disposition:
        return True

    # DDetection by URL pattern
    if "/download/" in target_url:
        return True

    return False


def create_file_response(response):
    """
    Create an HttpResponse for a file.
    """
    content_type = response.headers.get("Content-Type", "application/octet-stream")
    content_disposition = response.headers.get("Content-Disposition", "")

    logger.info(f"Creating file response: {content_type}")

    http_response = HttpResponse(
        response.content, status=response.status_code, content_type=content_type
    )

    # Set Content-Disposition if present
    if content_disposition:
        http_response["Content-Disposition"] = content_disposition

    return http_response
