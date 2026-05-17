import threading
import time
from datetime import datetime, date
from django.utils import timezone
from .models import Collection
from collectors.factories.fetcher_factory import FetcherFactory
from collectors.domain.entities.metrics_config import get_required_endpoints
from collectors.infrastructure.storage.minio_client import MinIOClient
from kafka_utils.client import KafkaClient
from kafka_utils.topics import Topics
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Collection Cancellation Registry
# =============================================================================

class CollectionCancelledException(Exception):
    """Raised when a collection is cancelled/deleted during execution"""
    pass


class CancellationRegistry:
    """
    Thread-safe registry to track cancelled collections.
    When a collection is deleted, it gets registered here so the background
    thread knows to stop immediately.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._cancelled_collections = set()
                    cls._instance._registry_lock = threading.Lock()
        return cls._instance
    
    def cancel(self, collection_id: int):
        """Register a collection as cancelled"""
        with self._registry_lock:
            self._cancelled_collections.add(collection_id)
            logger.info(
                "Collection marked for cancellation",
                extra={"collection_id": collection_id, "event": "collection_cancel_requested"},
            )
    
    def is_cancelled(self, collection_id: int) -> bool:
        """Check if a collection is cancelled"""
        with self._registry_lock:
            return collection_id in self._cancelled_collections
    
    def remove(self, collection_id: int):
        """Remove a collection from the cancelled set (cleanup)"""
        with self._registry_lock:
            self._cancelled_collections.discard(collection_id)


# Global cancellation registry instance
cancellation_registry = CancellationRegistry()


def run_collection_in_background(plan_id, resume=False):
    """Start collection in a separate thread"""
    thread = threading.Thread(target=execute_collection_task, args=(plan_id, resume))
    thread.daemon = True
    thread.start()
    logger.info(
        "Background collection thread started",
        extra={"collection_id": plan_id, "resume": resume, "event": "collection_thread_started"},
    )


def execute_collection_task(plan_id, resume=False):
    """Execute the actual collection task with incremental saving"""
    minio_client = MinIOClient()
    raw_data_filename = None  # Track the filename for cleanup on cancellation
    collection = None
    _task_start = time.monotonic()

    try:
        # Check if already cancelled before starting
        if cancellation_registry.is_cancelled(plan_id):
            logger.info(
                "Collection cancelled before starting",
                extra={"collection_id": plan_id, "status": "cancelled", "event": "collection_skipped"},
            )
            cancellation_registry.remove(plan_id)
            return
        
        collection = Collection.objects.get(id=plan_id)
        raw_data_filename = collection.raw_data_filename  # Store for potential cleanup
        
        # Update status
        collection.status = "in_progress"
        if not resume:
            collection.started_at = timezone.now()
            collection.last_collected_item_id = None
        collection.save()

        KafkaClient.publish(
            Topics.COLLECTION_STARTED,
            {
                'collection_id': collection.id,
                'user_id': collection.user,
                'workspace_id': collection.workspace_id,
                'repository_id': collection.repository_id,
                'status': 'in_progress',
            },
        )
        
        logger.info(
            "Collection started",
            extra={
                "collection_id": collection.id,
                "repository": collection.repository_full_name,
                "platform": collection.platform,
                "branch": collection.branch_name,
                "resume": resume,
                "status": "started",
                "event": "collection_started",
            },
        )

        # Prepare filters
        filters = collection.filters.copy()
        if filters.get("start_date"):
            filters["start_date"] = date.fromisoformat(filters["start_date"])
        if filters.get("end_date"):
            filters["end_date"] = date.fromisoformat(filters["end_date"])

        # Load existing data if resuming
        existing_data = {}
        if resume and collection.raw_data_filename:
            existing_data = minio_client.get_json(collection.raw_data_filename) or {}
        
        # Compute required endpoints based on selected metrics
        selected_metrics = collection.selected_metrics or []
        required_endpoints = get_required_endpoints(collection.platform, selected_metrics) if selected_metrics else None
        logger.info(
            "Collection metrics resolved",
            extra={
                "collection_id": collection.id,
                "repository": collection.repository_full_name,
                "selected_metrics": selected_metrics,
                "required_endpoints": required_endpoints,
                "event": "collection_metrics_resolved",
            },
        )

        # Initialize collector via factory (decouples task from concrete types)
        collector = FetcherFactory.create(
            platform=collection.platform,
            token=collection.token_encrypted,
            repo_full_name=collection.repository_full_name,
            branch_name=collection.branch_name,
            selected_metrics=selected_metrics,
            project_id=collection.external_id,
        )
        collector.required_endpoints = required_endpoints
        
        # Progress callback with batched saving
        batch_size = collection.save_batch_size or 1
        items_since_last_save = 0
        _collection_start = time.monotonic()

        def save_progress(current, total, message="", item_data=None, all_data=None):
            nonlocal items_since_last_save, raw_data_filename
            try:
                # Check if collection was paused or cancelled
                if cancellation_registry.is_cancelled(plan_id):
                    cancellation_registry.remove(plan_id)
                    logger.info(
                        "Collection stopped by cancellation registry",
                        extra={
                            "collection_id": plan_id,
                            "repository": collection.repository_full_name,
                            "status": "cancelled",
                            "event": "collection_cancelled",
                            "progress": current,
                            "total": total,
                        },
                    )
                    raise CollectionCancelledException(f"Collection {plan_id} was stopped")

                collection.refresh_from_db()
                collection.collected_items = current
                collection.total_items = total
                
                # Save accumulated data in batches (all_data is managed by the collector)
                if item_data and all_data is not None:
                    # Update last collected item
                    item_number = item_data.get("pull_request_number") or item_data.get(
                        "merge_request_id"
                    )
                    collection.last_collected_item_id = str(item_number)

                    if not collection.raw_data_filename:
                        collection.raw_data_filename = minio_client.generate_filename(
                            collection.repository_name, collection.id, "json"
                        )
                        raw_data_filename = collection.raw_data_filename

                    items_since_last_save += 1

                    # Save to MinIO only when batch is full
                    if items_since_last_save >= batch_size:
                        _batch_start = time.monotonic()
                        minio_client.save_json(all_data, collection.raw_data_filename)
                        _batch_duration = round(time.monotonic() - _batch_start, 3)
                        items_since_last_save = 0
                        logger.info(
                            "Batch saved to MinIO",
                            extra={
                                "collection_id": plan_id,
                                "repository": collection.repository_full_name,
                                "progress": current,
                                "total": total,
                                "batch_size": batch_size,
                                "duration": _batch_duration,
                                "event": "collection_batch_saved",
                            },
                        )
                
                collection.save(update_fields=['collected_items', 'total_items', 'last_collected_item_id', 'raw_data_filename'])
                logger.debug(
                    "Collection progress updated",
                    extra={
                        "collection_id": plan_id,
                        "repository": collection.repository_full_name,
                        "progress": current,
                        "total": total,
                        "message": message,
                        "event": "collection_progress",
                    },
                )
            except Collection.DoesNotExist:
                logger.warning(
                    "Collection deleted during progress save",
                    extra={
                        "collection_id": plan_id,
                        "event": "collection_deleted_during_run",
                        "status": "cancelled",
                    },
                )
                if raw_data_filename:
                    try:
                        minio_client.delete_file(raw_data_filename)
                        raw_data_filename = None
                    except Exception:
                        pass
                raise CollectionCancelledException(f"Collection {plan_id} was deleted")
            except CollectionCancelledException:
                raise
            except Exception as e:
                logger.error(
                    "Error saving collection progress",
                    extra={
                        "collection_id": plan_id,
                        "repository": collection.repository_full_name,
                        "error": str(e),
                        "event": "collection_progress_error",
                        "status": "error",
                    },
                )

        # Collect data
        logger.info(
            "Data collection phase starting",
            extra={
                "collection_id": collection.id,
                "repository": collection.repository_full_name,
                "platform": collection.platform,
                "event": "collection_data_fetch_start",
            },
        )
        _fetch_start = time.monotonic()
        all_data = collector.collect_all_data(
            filters=filters,
            progress_callback=save_progress,
            resume_from=collection.last_collected_item_id if resume else None,
            existing_data=existing_data if resume else None,
        )

        # Update is_total_approximate from collector
        if hasattr(collector, 'is_total_approximate'):
            collection.is_total_approximate = collector.is_total_approximate

        _fetch_duration = round(time.monotonic() - _fetch_start, 3)

        # Calculate statistics
        stats = calculate_statistics(all_data, collection.platform)

        # Update collection
        collection.stats = stats
        collection.total_items = stats.get("total_items", 0)
        collection.status = "completed"
        collection.completed_at = timezone.now()

        # Generate final filename if not set
        if not collection.raw_data_filename:
            collection.raw_data_filename = minio_client.generate_filename(
                collection.repository_name, collection.id, "json"
            )

        # Save final data
        _minio_start = time.monotonic()
        minio_client.save_json(all_data, collection.raw_data_filename)
        _minio_duration = round(time.monotonic() - _minio_start, 3)

        collection.save()

        _total_duration = round(time.monotonic() - _task_start, 3)

        KafkaClient.publish(
            Topics.COLLECTION_COMPLETED,
            {
                'collection_id': collection.id,
                'user_id': collection.user,
                'workspace_id': collection.workspace_id,
                'repository_id': collection.repository_id,
                'status': 'completed',
                'result_summary': stats,
            },
        )
        
        logger.info(
            "Collection completed successfully",
            extra={
                "collection_id": collection.id,
                "repository": collection.repository_full_name,
                "platform": collection.platform,
                "status": "success",
                "total_items": stats.get("total_items", 0),
                "duration": _total_duration,
                "fetch_duration": _fetch_duration,
                "minio_save_duration": _minio_duration,
                "minio_filename": collection.raw_data_filename,
                "stats": stats,
                "event": "collection_completed",
            },
        )
        
    except Collection.DoesNotExist:
        logger.error(
            "Collection not found",
            extra={"collection_id": plan_id, "status": "error", "event": "collection_not_found"},
        )
        cancellation_registry.remove(plan_id)
    except CollectionCancelledException as e:
        _total_duration = round(time.monotonic() - _task_start, 3)
        logger.info(
            "Collection was cancelled",
            extra={
                "collection_id": plan_id,
                "status": "cancelled",
                "duration": _total_duration,
                "reason": str(e),
                "event": "collection_cancelled",
            },
        )
        cancellation_registry.remove(plan_id)
        # Only clean up MinIO file if the collection was fully deleted (not paused)
        try:
            Collection.objects.get(id=plan_id)
            # Collection still exists (paused) — keep MinIO data
            logger.info(
                "Collection paused, keeping MinIO data",
                extra={"collection_id": plan_id, "status": "paused", "event": "collection_paused"},
            )
        except Collection.DoesNotExist:
            # Collection was deleted — clean up MinIO file
            if raw_data_filename:
                try:
                    minio_client.delete_file(raw_data_filename)
                    logger.info(
                        "MinIO file cleaned up after deletion",
                        extra={
                            "collection_id": plan_id,
                            "minio_filename": raw_data_filename,
                            "event": "collection_minio_cleanup",
                        },
                    )
                except Exception as cleanup_error:
                    logger.warning(
                        "Could not clean up MinIO file during cancellation",
                        extra={
                            "collection_id": plan_id,
                            "minio_filename": raw_data_filename,
                            "error": str(cleanup_error),
                            "event": "collection_minio_cleanup_failed",
                        },
                    )
    except Exception as e:
        _total_duration = round(time.monotonic() - _task_start, 3)
        logger.error(
            "Collection failed with unexpected error",
            extra={
                "collection_id": plan_id,
                "repository": collection.repository_full_name if collection else None,
                "status": "failed",
                "error": str(e),
                "duration": _total_duration,
                "event": "collection_failed",
            },
            exc_info=True,
        )
        cancellation_registry.remove(plan_id)
        
        try:
            collection = Collection.objects.get(id=plan_id)
            collection.status = (
                "paused" if collection.last_collected_item_id else "failed"
            )
            collection.error_message = str(e)
            collection.paused_at = (
                timezone.now() if collection.last_collected_item_id else None
            )
            collection.save()
        except Exception:
            pass
        finally:
            if collection:
                try:
                    KafkaClient.publish(
                        Topics.COLLECTION_FAILED,
                        {
                            'collection_id': collection.id,
                            'user_id': collection.user,
                            'workspace_id': collection.workspace_id,
                            'repository_id': collection.repository_id,
                            'status': 'failed',
                            'error': str(e),
                        },
                    )
                except Exception as publish_error:
                    logger.warning(
                        "Could not publish COLLECTION_FAILED event",
                        extra={
                            "collection_id": plan_id,
                            "error": str(publish_error),
                            "event": "kafka_publish_failed",
                        },
                    )


def calculate_statistics(all_data, platform):
    """Calculate statistics from collected data"""
    stats = {"total_items": 0}

    if platform == "github":
        prs = all_data.get("pull_requests", [])
        stats["pull_requests_count"] = len(prs)
        stats["total_items"] = len(prs)

        total_commits = sum(len(pr.get("commits", [])) for pr in prs)
        total_comments = sum(len(pr.get("comments", [])) for pr in prs)
        total_reviews = sum(len(pr.get("reviews", [])) for pr in prs)
        total_review_comments = sum(len(pr.get("review_comments", [])) for pr in prs)

        stats["commits_count"] = total_commits
        stats["comments_count"] = total_comments
        stats["reviews_count"] = total_reviews
        stats["review_comments_count"] = total_review_comments

        all_dates = []
        for pr in prs:
            if pr.get("details", {}).get("created_at"):
                try:
                    date_obj = datetime.fromisoformat(
                        pr["details"]["created_at"].replace("Z", "+00:00")
                    )
                    all_dates.append(date_obj)
                except:
                    pass

        if all_dates:
            stats["start_date"] = min(all_dates).strftime("%d/%m/%Y")
            stats["end_date"] = max(all_dates).strftime("%d/%m/%Y")

    else:  # GitLab
        mrs = all_data.get("merge_requests", [])
        stats["merge_requests_count"] = len(mrs)
        stats["total_items"] = len(mrs)

        total_commits = sum(len(mr.get("commits", [])) for mr in mrs)
        total_notes = sum(len(mr.get("notes", [])) for mr in mrs)
        total_discussions = sum(len(mr.get("discussions", [])) for mr in mrs)

        stats["commits_count"] = total_commits
        stats["notes_count"] = total_notes
        stats["discussions_count"] = total_discussions

        all_dates = []
        for mr in mrs:
            if mr.get("details", {}).get("created_at"):
                try:
                    date_obj = datetime.fromisoformat(
                        mr["details"]["created_at"].replace("Z", "+00:00")
                    )
                    all_dates.append(date_obj)
                except:
                    pass

        if all_dates:
            stats["start_date"] = min(all_dates).strftime("%d/%m/%Y")
            stats["end_date"] = max(all_dates).strftime("%d/%m/%Y")

    return stats
