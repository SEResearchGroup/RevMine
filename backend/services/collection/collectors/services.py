"""Collection Services Layer - Business logic for the collection service."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple

from django.utils import timezone
from django.db import transaction
from kafka_utils.request_reply import RequestReplyClient
from kafka_utils.topics import Topics

from .models import Collection, CleanedData
from .branch_fetcher import BranchFetcher
from .metrics_config import get_metrics_for_platform
from .minio_client import MinIOClient
from .csv_generator import CSVGenerator, StatisticsCSVGenerator
from .tasks import run_collection_in_background, cancellation_registry
from .serializers import CollectionSerializer, CleanedDataSerializer
from .metadata_extractor import _ReplayStream
import ijson

logger = logging.getLogger(__name__)

_rr_client: RequestReplyClient | None = None


def _get_rr_client() -> RequestReplyClient:
    global _rr_client
    if _rr_client is None:
        _rr_client = RequestReplyClient()
    return _rr_client


def resolve_workspace_token(user_id: int, workspace_id: int, platform: str) -> str:
    """Retrieve workspace token from configuration service through Kafka request-reply."""
    response = _get_rr_client().call(
        request_topic=Topics.TOKENS_REQUEST,
        response_topic=Topics.TOKENS_RESPONSE,
        payload={
            'user_id': user_id,
            'workspace_id': workspace_id,
        },
        timeout=10,
    )

    if not response or response.get('status') != 'ok':
        raise CollectionValidationError(
            f"Could not retrieve workspace token from configuration service: {response}"
        )

    token = response.get('token')
    if not token:
        raise CollectionValidationError('Token missing in configuration service response')

    response_platform = response.get('platform')
    if response_platform and response_platform != platform:
        logger.warning(
            "Workspace platform mismatch between collection request (%s) and configuration (%s)",
            platform,
            response_platform,
        )

    return token


def _normalize_raw_data(raw_data, platform: str):
    """Normalize raw data: external uploads may be a plain list instead of a dict."""
    if isinstance(raw_data, list):
        item_key = 'pull_requests' if platform == 'github' else 'merge_requests'
        return {item_key: raw_data}
    return raw_data


def _extract_files_from_item(item: dict, platform: str) -> list:
    """Extract the list of modified files from an item, handling both platforms."""
    if platform == 'github':
        return item.get('files', [])
    # GitLab: files are nested inside item['changes']['changes']
    changes = item.get('changes', {})
    if isinstance(changes, dict):
        return changes.get('changes', []) or changes.get('diffs', [])
    return []


# =============================================================================
# Exceptions for Service Layer
# =============================================================================


class CollectionServiceError(Exception):
    """Base exception for collection service errors."""

    pass


class CollectionNotFoundError(CollectionServiceError):
    """Collection not found."""

    pass


class CollectionPermissionError(CollectionServiceError):
    """Permission denied."""

    pass


class CollectionValidationError(CollectionServiceError):
    """Validation failed."""

    pass


class CollectionStateError(CollectionServiceError):
    """Invalid state for operation."""

    pass


class StorageError(CollectionServiceError):
    """Storage operation failed."""

    pass


# =============================================================================
# Metrics and Branches Services
# =============================================================================


class MetricsService:
    """Service for metrics operations."""

    @staticmethod
    def get_available_metrics(platform: str) -> List[Dict]:
        """Get available metrics for a platform."""
        return get_metrics_for_platform(platform)

    @staticmethod
    def get_metrics_with_collection_status(
        user_id: int, repository_id: int, platform: str
    ) -> Dict[str, Any]:
        """Get available metrics and check for active collection."""
        existing_collection = Collection.get_active_for_repository(
            user_id=user_id, repository_id=repository_id
        )

        return {
            "available_metrics": get_metrics_for_platform(platform),
            "platform": platform,
            "has_active_collection": existing_collection is not None,
            "active_collection": existing_collection,
        }


class BranchService:
    """Service for branch operations."""

    @staticmethod
    def fetch_branches(platform: str, token: str, repo_full_name: str) -> List[Dict]:
        """Fetch branches for a repository."""
        try:
            branch_fetcher = BranchFetcher(
                platform=platform, token=token, repo_full_name=repo_full_name
            )
            return branch_fetcher.fetch_branches()
        except Exception as e:
            logger.error(f"Error fetching branches: {e}")
            raise CollectionServiceError(f"Failed to fetch branches: {str(e)}")

    @staticmethod
    def fetch_branches_for_collection(collection: Collection) -> List[Dict]:
        """Fetch branches using collection stored credentials."""
        return BranchService.fetch_branches(
            platform=collection.platform,
            token=collection.token_encrypted,
            repo_full_name=collection.repository_full_name,
        )

    @staticmethod
    def fetch_date_range(platform: str, token: str, repo_full_name: str) -> Dict[str, Any]:
        """Fetch the global date range of MRs/PRs for a repository."""
        try:
            branch_fetcher = BranchFetcher(
                platform=platform, token=token, repo_full_name=repo_full_name
            )
            return branch_fetcher.fetch_date_range()
        except Exception as e:
            logger.error(f"Error fetching date range: {e}")
            return {"first_date": None, "last_date": None}


# =============================================================================
# Collection Lifecycle Services
# =============================================================================


class CollectionService:
    """Service for collection lifecycle operations."""

    IN_PROGRESS_STALE_THRESHOLD = 5  # minutes
    PENDING_STALE_THRESHOLD = 10  # minutes

    @staticmethod
    def _mark_stale_collections(
        existing_collection: Optional[Collection],
    ) -> Optional[Collection]:
        """Mark stale collections as paused/failed. Returns None if marked stale."""
        if not existing_collection:
            return None

        now = timezone.now()

        if existing_collection.status == "in_progress":
            stale_threshold = now - timedelta(
                minutes=CollectionService.IN_PROGRESS_STALE_THRESHOLD
            )
            check_time = (
                existing_collection.started_at or existing_collection.created_at
            )

            if check_time < stale_threshold:
                logger.info(
                    f"Marking stale in_progress collection {existing_collection.id} as paused "
                    f"(started: {check_time})"
                )
                existing_collection.status = "paused"
                existing_collection.error_message = (
                    "Collection was interrupted (detected as stale)"
                )
                existing_collection.save()
                return None

        elif existing_collection.status == "pending":
            stale_threshold = now - timedelta(
                minutes=CollectionService.PENDING_STALE_THRESHOLD
            )

            if existing_collection.created_at < stale_threshold:
                logger.info(
                    f"Marking stale pending collection {existing_collection.id} as failed "
                    f"(created: {existing_collection.created_at})"
                )
                existing_collection.status = "failed"
                existing_collection.error_message = "Collection was never started"
                existing_collection.save()
                return None

        return existing_collection

    @staticmethod
    @transaction.atomic
    def get_or_create_collection(
        user_id: int, validated_data: Dict[str, Any]
    ) -> Tuple[Collection, bool]:
        """Get existing active collection or create a new one (idempotent)."""
        repository_id = validated_data["repository_id"]
        platform = validated_data["platform"]

        # Check for any active collection
        existing_collection = Collection.get_active_for_repository(
            user_id=user_id, repository_id=repository_id
        )

        # Mark stale collections
        existing_collection = CollectionService._mark_stale_collections(
            existing_collection
        )

        if existing_collection:
            logger.info(
                f"Active collection already exists for user {user_id}, "
                f"repository {repository_id} (collection id={existing_collection.id}, "
                f"status={existing_collection.status})"
            )
            return existing_collection, True

        # Double-check within transaction with lock
        existing_check = (
            Collection.objects.select_for_update()
            .filter(
                user=user_id,
                repository_id=repository_id,
                status__in=Collection.ACTIVE_STATUSES,
            )
            .first()
        )

        if existing_check:
            existing_check = CollectionService._mark_stale_collections(existing_check)
            if existing_check:
                return existing_check, True
        
        token = validated_data.get('token')
        if not token:
            token = resolve_workspace_token(
                user_id=user_id,
                workspace_id=validated_data['workspace_id'],
                platform=platform,
            )

        # Create new collection
        collection = Collection.objects.create(
            user=user_id,
            workspace_id=validated_data["workspace_id"],
            repository_id=repository_id,
            repository_name=validated_data["repository_name"],
            repository_full_name=validated_data["repository_full_name"],
            platform=platform,
            repository_url=validated_data.get('repository_url'),
            default_branch=validated_data.get('default_branch'),
            external_id=validated_data.get('external_id'),
            token_encrypted=token,
            status='pending'
        )

        logger.info(
            f"New collection created for user {user_id}, "
            f"repository {repository_id} (collection id={collection.id})"
        )

        return collection, False

    @staticmethod
    def configure_metrics(
        collection: Collection,
        selected_metrics: List[str],
        filters: Dict[str, Any],
        branch_name: Optional[str] = None,
    ) -> Collection:
        """Configure metrics, filters, and branch for a collection."""
        allowed_statuses = ["pending", "failed", "paused"]
        if collection.status not in allowed_statuses:
            raise CollectionStateError(
                f"Can only configure metrics for {', '.join(allowed_statuses)} collections"
            )

        collection.selected_metrics = selected_metrics
        collection.filters = {
            "start_date": (
                filters.get("start_date").isoformat()
                if filters.get("start_date")
                else None
            ),
            "end_date": (
                filters.get("end_date").isoformat() if filters.get("end_date") else None
            ),
            "status": filters.get("status", []),
        }

        if branch_name is not None:
            collection.branch_name = branch_name

        save_batch_size = filters.get("save_batch_size")
        if save_batch_size is not None:
            collection.save_batch_size = max(1, min(100, int(save_batch_size)))

        collection.save()

        logger.info(
            f"Metrics configured for collection {collection.id}: {selected_metrics}"
        )

        return collection

    @staticmethod
    def get_collection_summary(collection: Collection) -> Dict[str, Any]:
        """Get collection summary for validation."""
        return {
            "repository": collection.repository_full_name,
            "platform": collection.platform,
            "branch": collection.branch_name or collection.default_branch,
            "metrics_count": len(collection.selected_metrics),
            "metrics": collection.selected_metrics,
            "filters": collection.filters,
        }

    @staticmethod
    def execute_collection(collection: Collection) -> Collection:
        """Start data collection in background."""
        if collection.status not in ["pending", "failed"]:
            raise CollectionStateError(
                f"Cannot start collection with status: {collection.status}"
            )

        if not collection.selected_metrics:
            raise CollectionValidationError(
                "No metrics selected. Configure metrics first."
            )

        run_collection_in_background(collection.id)

        return collection

    @staticmethod
    def resume_collection(collection: Collection) -> Collection:
        """Resume a paused or failed collection."""
        if not collection.can_resume:
            raise CollectionStateError("Cannot resume this collection")

        run_collection_in_background(collection.id, resume=True)

        return collection

    @staticmethod
    def pause_collection(collection: Collection) -> Collection:
        """Pause a running collection. Keeps data in DB and MinIO for later resume."""
        if collection.status != "in_progress":
            raise CollectionStateError(
                f"Cannot pause collection with status: {collection.status}"
            )

        # Signal the background thread to stop
        cancellation_registry.cancel(collection.id)

        # Update status to paused
        collection.status = "paused"
        collection.paused_at = timezone.now()
        collection.error_message = "Collection paused by user"
        collection.save()

        logger.info(f"Collection {collection.id} paused by user")
        return collection

    @staticmethod
    def get_collection_status(collection: Collection) -> Dict[str, Any]:
        """Get the current status of a collection."""
        return {
            "status": collection.status,
            "progress_percentage": collection.progress_percentage,
            "collected_items": collection.collected_items,
            "total_items": collection.total_items,
            "is_total_approximate": collection.is_total_approximate,
            "stats": collection.stats,
            "can_resume": collection.can_resume,
            "last_collected_item": collection.last_collected_item_id,
        }

    @staticmethod
    def get_user_collections(user_id: int) -> List[Collection]:
        """Get all collections for a user."""
        return Collection.objects.filter(user=user_id)

    @staticmethod
    def get_repository_history(user_id: int, repository_id: int) -> List[Collection]:
        """Get collection history for a repository (excludes pending)."""
        return Collection.objects.filter(
            user=user_id,
            repository_id=repository_id,
            status__in=["completed", "paused", "failed", "in_progress"],
        ).order_by("-created_at")

    @staticmethod
    def delete_collection(collection: Collection) -> None:
        """Delete a collection and all its related files.
        
        If the collection is in progress, it will be cancelled first
        to stop the background collection task immediately.
        """
        try:
            collection_id = collection.id
            raw_data_filename = collection.raw_data_filename
            is_in_progress = collection.status == 'in_progress'
            
            # If collection is in progress, register it for cancellation
            # This will signal the background thread to stop immediately
            if is_in_progress:
                cancellation_registry.cancel(collection_id)
                logger.info(f"Collection {collection_id} is in progress, registered for cancellation")
            
            minio_client = MinIOClient()

            # Delete all cleaning files
            for cleaned_data in collection.cleaned_data.all():
                if cleaned_data.structured_csv_filename:
                    minio_client.delete_file(cleaned_data.structured_csv_filename)
                if cleaned_data.statistics_csv_filename:
                    minio_client.delete_file(cleaned_data.statistics_csv_filename)

            # Delete raw data file
            if raw_data_filename:
                minio_client.delete_file(raw_data_filename)
            
            # Delete legacy CSV files if they exist
            if collection.structured_csv_filename:
                minio_client.delete_file(collection.structured_csv_filename)
            if collection.statistics_csv_filename:
                minio_client.delete_file(collection.statistics_csv_filename)

            # Delete collection (cascade will delete cleaned data)
            collection.delete()

            logger.info(f"Collection {collection_id} deleted successfully")

        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise StorageError(f"Failed to delete collection: {str(e)}")


# =============================================================================
# Collected Data Services
# =============================================================================


class CollectedDataService:
    """Service for collected data operations."""

    @staticmethod
    def get_collected_data(collection: Collection) -> Dict[str, Any]:
        """Get collected data from MinIO."""
        try:
            minio_client = MinIOClient()

            if collection.raw_data_filename:
                raw_data = minio_client.get_json(collection.raw_data_filename)

                if raw_data:
                    return {
                        "collection_plan_id": collection.id,
                        "raw_data": raw_data,
                        "stats": collection.stats,
                        "filename": collection.raw_data_filename,
                        "platform": collection.platform,
                        "found": True,
                    }
                else:
                    logger.error(
                        f"File {collection.raw_data_filename} not found in MinIO"
                    )
                    return {
                        "collection_plan_id": collection.id,
                        "raw_data": {},
                        "stats": collection.stats,
                        "message": "Data file not found in storage",
                        "platform": collection.platform,
                        "found": False,
                    }
            else:
                return {
                    "collection_plan_id": collection.id,
                    "raw_data": {},
                    "stats": collection.stats,
                    "message": "No data collected yet",
                    "platform": collection.platform,
                    "found": False,
                }

        except Exception as e:
            logger.error(f"Error retrieving data from MinIO: {e}")
            raise StorageError(f"Failed to retrieve collected data: {str(e)}")

    @staticmethod
    def get_raw_json(collection: Collection) -> Optional[bytes]:
        """Get raw JSON data for download."""
        if not collection.raw_data_filename:
            return None

        try:
            minio_client = MinIOClient()
            json_data = minio_client.get_json(collection.raw_data_filename)
            return json_data
        except Exception as e:
            logger.error(f"Error downloading JSON: {e}")
            return None


# =============================================================================
# Data Cleaning Services
# =============================================================================


class DataCleaningService:
    """Service for data cleaning operations."""

    @staticmethod
    def get_cleaning_config(collection: Collection) -> Dict[str, Any]:
        """Get available filters for cleaning a completed collection."""
        if collection.status != 'completed':
            raise CollectionStateError('Can only clean completed collections')
        
        # Use pre-computed metadata if available (external uploads)
        if collection.cleaning_metadata:
            meta = collection.cleaning_metadata
            return {
                'collection_plan_id': collection.id,
                'platform': collection.platform,
                'total_items': meta.get('total_items', 0),
                'available_filters': {
                    'authors': meta.get('authors', []),
                    'file_extensions': meta.get('file_extensions', []),
                }
            }
        
        # Fallback: load from MinIO (for non-external / legacy collections)
        minio_client = MinIOClient()

        if not collection.raw_data_filename:
            raise StorageError("No raw data file found")

        raw_data = minio_client.get_json(collection.raw_data_filename)

        if not raw_data:
            raise StorageError('Raw data not found in storage')
        
        raw_data = _normalize_raw_data(raw_data, collection.platform)
        
        # Extract metadata for filters
        item_key = (
            "pull_requests" if collection.platform == "github" else "merge_requests"
        )
        items = raw_data.get(item_key, [])

        # Get unique authors and file extensions
        authors = set()
        file_extensions = set()

        for item in items:
            # Authors
            author = item.get("details", {}).get("user", {}).get("login") or item.get(
                "details", {}
            ).get("author", {}).get("username")
            if author:
                authors.add(author)

            # File extensions
            files = _extract_files_from_item(item, collection.platform)
            for file in files:
                filename = file.get("filename") or file.get("new_path")
                if filename and "." in filename:
                    ext = filename.split(".")[-1]
                    file_extensions.add(f".{ext}")

        return {
            "collection_plan_id": collection.id,
            "platform": collection.platform,
            "total_items": len(items),
            "available_filters": {
                "authors": sorted(list(authors)),
                "file_extensions": sorted(list(file_extensions)),
            },
        }

    @staticmethod
    def apply_filters_and_create_csv(
        collection: Collection, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply filters and create structured CSV files."""
        minio_client = MinIOClient()

        if not collection.raw_data_filename:
            raise StorageError("No raw data file found")

        raw_data = minio_client.get_json(collection.raw_data_filename)
        if not raw_data:
            raise StorageError('Raw data not found in storage')
        
        raw_data = _normalize_raw_data(raw_data, collection.platform)
        
        # Apply filters and generate CSV
        csv_generator = CSVGenerator(collection.platform)
        filtered_data = csv_generator.apply_filters(raw_data, filters)
        csv_content = csv_generator.generate_csv(filtered_data)

        # Generate statistics CSV
        stats_generator = StatisticsCSVGenerator(collection.platform)
        stats_csv_content = stats_generator.generate_statistics_csv(
            filtered_data, collection
        )
        

        # Save structured CSV
        structured_filename = minio_client.generate_filename(
            collection.repository_name, collection.id, "csv"
        )
        minio_client.save_csv(csv_content, structured_filename)

        # Save statistics CSV
        stats_filename = f"{collection.repository_name}_stats_{collection.id}.csv"
        minio_client.save_csv(stats_csv_content, stats_filename)

        # Update collection
        collection.structured_csv_filename = structured_filename
        collection.statistics_csv_filename = stats_filename

        # Delete JSON if requested
        if filters.get("replace_json", False):
            minio_client.delete_file(collection.raw_data_filename)
            collection.raw_data_filename = None

        collection.save()

        # Get preview data
        preview_data = csv_generator.get_preview(filtered_data, rows=5)

        item_key = (
            "pull_requests" if collection.platform == "github" else "merge_requests"
        )
        filtered_count = len(filtered_data.get(item_key, []))

        return {
            "csv_filename": structured_filename,
            "statistics_filename": stats_filename,
            "replaced_json": filters.get("replace_json", False),
            "filtered_count": filtered_count,
            "preview": preview_data,
        }


# =============================================================================
# CleanedData Services
# =============================================================================


class CleanedDataService:
    """Service for CleanedData operations."""

    @staticmethod
    def get_cleaned_data_list(collection: Collection) -> List[CleanedData]:
        """Get all cleaned data for a collection."""
        return collection.cleaned_data.all()

    @staticmethod
    def create_cleaned_data(
        collection: Collection,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        filters: Optional[Dict] = None,
        selected_features: Optional[list] = None
    ) -> CleanedData:
        """Create a new cleaned data instance with filtered CSV files."""
        if collection.status != "completed":
            raise CollectionStateError("Collection must be completed before cleaning")

        # Create cleaned data instance
        cleaned_data = CleanedData.objects.create(
            collection=collection,
            start_date=start_date,
            end_date=end_date,
            filters=filters or {},
            selected_features=selected_features or [],
            status='in_progress'
        )

        try:
            # Get raw data - use streaming for external/large collections
            minio_client = MinIOClient()
            
            if collection.is_external:
                
                item_key = 'pull_requests' if collection.platform == 'github' else 'merge_requests'
                stream = minio_client.get_object_stream(collection.raw_data_filename)
                if not stream:
                    raise StorageError("Raw data not found in MinIO")
                
                try:
                    # Peek to detect format (list vs dict)
                    first_byte = b''
                    while True:
                        b = stream.read(1)
                        if not b:
                            break
                        if b not in (b' ', b'\n', b'\r', b'\t', b'\xef', b'\xbb', b'\xbf'):
                            first_byte = b
                            break
                    
                    is_list = (first_byte == b'[')
                    replayed = _ReplayStream(first_byte, stream)
                    prefix = 'item' if is_list else f'{item_key}.item'
                    
                    items = list(ijson.items(replayed, prefix))
                    raw_data = {item_key: items}
                finally:
                    stream.close()
                    stream.release_conn()
            else:
                raw_data = minio_client.get_json(collection.raw_data_filename)
                if not raw_data:
                    raise StorageError("Raw data not found in MinIO")
                raw_data = _normalize_raw_data(raw_data, collection.platform)
            
            # Apply date filters if provided
            filtered_data = CleanedDataService._filter_data_by_date(
                raw_data, start_date, end_date, collection.platform
            )

            # Generate CSVs
            csv_generator = CSVGenerator(collection.platform)

            # Apply additional filters from the cleaning request
            if filters:
                filtered_data = csv_generator.apply_filters(filtered_data, filters)

            structured_csv = csv_generator.generate_csv(filtered_data)

            stats_generator = StatisticsCSVGenerator(collection.platform)
            statistics_csv = stats_generator.generate_statistics_csv(filtered_data, collection, selected_features=selected_features)
            
            # Generate filenames for CSV files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_repo_name = (
                collection.repository_name.replace("/", "_").replace(" ", "_").lower()
            )
            structured_filename = f"{clean_repo_name}_cleaneddata{cleaned_data.id}_{timestamp}_structured.csv"
            statistics_filename = f"{clean_repo_name}_cleaneddata{cleaned_data.id}_{timestamp}_statistics.csv"

            minio_client.save_csv(structured_csv, structured_filename)
            minio_client.save_csv(statistics_csv, statistics_filename)

            # Update cleaned data
            cleaned_data.structured_csv_filename = structured_filename
            cleaned_data.statistics_csv_filename = statistics_filename
            cleaned_data.stats = CleanedDataService._calculate_stats(
                filtered_data, collection.platform
            )
            cleaned_data.status = "completed"
            cleaned_data.save()

            logger.info(f"CleanedData {cleaned_data.id} completed successfully")

            return cleaned_data

        except Exception as e:
            logger.error(f"Error creating cleaned data: {e}")
            cleaned_data.status = "failed"
            cleaned_data.error_message = str(e)
            cleaned_data.save()
            raise

    @staticmethod
    def _filter_data_by_date(
        raw_data: Dict,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        platform: str,
    ) -> Dict:
        """Filter data by date range."""
        if not start_date and not end_date:
            return raw_data

        filtered_data = {}
        item_type = "pull_requests" if platform == "github" else "merge_requests"

        if item_type in raw_data:
            filtered_items = []
            for item in raw_data[item_type]:
                created_date = item.get("details", {}).get("created_at", "")
                if created_date:
                    # Parse date and check range
                    item_date = datetime.fromisoformat(
                        created_date.replace("Z", "+00:00")
                    ).date()

                    if start_date and item_date < start_date:
                        continue
                    if end_date and item_date > end_date:
                        continue

                    filtered_items.append(item)

            filtered_data[item_type] = filtered_items

        return filtered_data

    @staticmethod
    def _calculate_stats(data: Dict, platform: str) -> Dict:
        """Calculate statistics for cleaned data."""
        stats = {}
        item_type = "pull_requests" if platform == "github" else "merge_requests"

        if item_type in data:
            items = data[item_type]
            stats[f"{item_type}_count"] = len(items)
            stats["commits_count"] = sum(len(item.get("commits", [])) for item in items)

            if platform == "github":
                stats["comments_count"] = sum(
                    len(item.get("comments", [])) + len(item.get("reviews", []))
                    for item in items
                )
            else:
                stats["notes_count"] = sum(
                    len(item.get("notes", [])) + len(item.get("discussions", []))
                    for item in items
                )

        return stats

    @staticmethod
    def delete_cleaned_data(cleaned_data: CleanedData) -> None:
        """Delete a cleaned data instance and its files."""
        try:
            minio_client = MinIOClient()

            if cleaned_data.structured_csv_filename:
                minio_client.delete_file(cleaned_data.structured_csv_filename)
            if cleaned_data.statistics_csv_filename:
                minio_client.delete_file(cleaned_data.statistics_csv_filename)

            cleaned_data.delete()

        except Exception as e:
            logger.error(f"Error deleting cleaned data: {e}")
            raise StorageError(f"Failed to delete cleaned data: {str(e)}")

    @staticmethod
    def get_csv_for_download(
        cleaned_data: CleanedData, file_type: str
    ) -> Optional[bytes]:
        """Get CSV file bytes for download."""
        if file_type not in ["structured", "statistics"]:
            raise CollectionValidationError("Invalid file type")

        filename = (
            cleaned_data.structured_csv_filename
            if file_type == "structured"
            else cleaned_data.statistics_csv_filename
        )

        if not filename:
            return None

        try:
            minio_client = MinIOClient()
            return minio_client.get_csv_bytes(filename)
        except Exception as e:
            logger.error(f"Error getting CSV for download: {e}")
            return None

# =============================================================================
# User Datasets Service
# =============================================================================

class UserDatasetsService:
    """Service for user datasets operations."""
    
    @staticmethod
    def get_user_datasets(user_id: int) -> Dict[str, Any]:
        """Get all datasets (collections and cleaned data) for a user."""
        logger.info(f"Fetching datasets for user {user_id}")
        
        # Query collections with related data
        collections_query = Collection.objects.filter(user=user_id)
        collections = collections_query.select_related().prefetch_related('cleaned_data')
        
        # Serialize collections
        collections_data = CollectionSerializer(collections, many=True).data
        
        # Build cleaned datasets list with collection context
        cleaned_data_list = UserDatasetsService._build_cleaned_datasets_list(collections)
        
        # Calculate statistics
        statistics = UserDatasetsService._calculate_user_statistics(collections)
        
        response_data = {
            'user_id': user_id,
            'total_collections': collections.count(),
            'collections': collections_data,
            'total_cleaned_datasets': len(cleaned_data_list),
            'cleaned_datasets': cleaned_data_list,
            'statistics': statistics
        }
        
        logger.info(f"Returning {collections.count()} collections for user {user_id}")
        
        return response_data
    
    @staticmethod
    def _build_cleaned_datasets_list(collections) -> List[Dict[str, Any]]:
        """Build cleaned datasets list with collection context."""
        cleaned_data_list = []
        
        for collection in collections:
            cleaned_items = collection.cleaned_data.all()
            for cleaned in cleaned_items:
                cleaned_data_list.append({
                    **CleanedDataSerializer(cleaned).data,
                    'collection_id': collection.id,
                    'repository_name': collection.repository_name,
                    'repository_full_name': collection.repository_full_name,
                    'platform': collection.platform,
                    'repository_url': collection.repository_url,
                    'repository_id': collection.repository_id,
                    'workspace_id': collection.workspace_id,
                })
        
        return cleaned_data_list
    
    @staticmethod
    def _calculate_user_statistics(collections) -> Dict[str, int]:
        """Calculate global statistics for user's collections."""
        return {
            'total_items_collected': sum(c.collected_items for c in collections),
            'active_collections': collections.filter(status__in=Collection.ACTIVE_STATUSES).count(),
            'completed_collections': collections.filter(status='completed').count(),
            'failed_collections': collections.filter(status='failed').count(),
        }
