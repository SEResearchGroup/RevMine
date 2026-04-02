import threading
from datetime import datetime, date
from django.utils import timezone
from .models import Collection
from .github_collector import GitHubCollector
from .gitlab_collector import GitLabCollector
from .metrics_config import get_required_endpoints
from .minio_client import MinIOClient
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
            logger.info(f"Collection {collection_id} marked for cancellation")
    
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
        f"Started background collection for collection {plan_id} (resume={resume})"
    )


def execute_collection_task(plan_id, resume=False):
    """Execute the actual collection task with incremental saving"""
    minio_client = MinIOClient()
    raw_data_filename = None  # Track the filename for cleanup on cancellation
    collection = None
    
    try:
        # Check if already cancelled before starting
        if cancellation_registry.is_cancelled(plan_id):
            logger.info(f"Collection {plan_id} was cancelled before starting")
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
        
        logger.info(f"Starting collection for {plan_id} (resume={resume})")

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
        logger.info(f"Selected metrics: {selected_metrics}")
        logger.info(f"Required endpoints: {required_endpoints}")

        # Initialize collector with resume capability
        if collection.platform == "github":
            collector = GitHubCollector(
                token=collection.token_encrypted,
                repo_full_name=collection.repository_full_name,
                branch_name=collection.branch_name,
                selected_metrics=selected_metrics
            )
        else:
            collector = GitLabCollector(
                token=collection.token_encrypted,
                repo_full_name=collection.repository_full_name,
                branch_name=collection.branch_name,
                project_id=collection.external_id,  
                selected_metrics=selected_metrics
            )
        collector.required_endpoints = required_endpoints
        
        # Progress callback with incremental saving
        def save_progress(current, total, message="", item_data=None, all_data=None):
            try:
                # Check if collection was paused or cancelled
                if cancellation_registry.is_cancelled(plan_id):
                    cancellation_registry.remove(plan_id)
                    logger.info(f"Collection {plan_id} stopped by cancellation registry")
                    raise CollectionCancelledException(f"Collection {plan_id} was stopped")

                collection.refresh_from_db()
                collection.collected_items = current
                collection.total_items = total
                
                # Save accumulated data incrementally (all_data is managed by the collector)
                if item_data and all_data is not None:
                    # Update last collected item
                    item_number = item_data.get("pull_request_number") or item_data.get(
                        "merge_request_id"
                    )
                    collection.last_collected_item_id = str(item_number)

                    # Save to MinIO after each item
                    if not collection.raw_data_filename:
                        collection.raw_data_filename = minio_client.generate_filename(
                            collection.repository_name, collection.id, "json"
                        )
                        raw_data_filename = collection.raw_data_filename
                    
                    minio_client.save_json(all_data, collection.raw_data_filename)
                
                collection.save(update_fields=['collected_items', 'total_items', 'last_collected_item_id', 'raw_data_filename'])
                logger.info(f"Progress: {current}/{total} - {message}")
            except Collection.DoesNotExist:
                logger.info(f"Collection {plan_id} was deleted during progress save")
                if raw_data_filename:
                    try:
                        minio_client.delete_file(raw_data_filename)
                    except:
                        pass
                raise CollectionCancelledException(f"Collection {plan_id} was deleted")
            except CollectionCancelledException:
                raise
            except Exception as e:
                logger.error(f"Error saving progress: {e}")

        # Collect data
        logger.info("Starting data collection...")
        all_data = collector.collect_all_data(
            filters=filters,
            progress_callback=save_progress,
            resume_from=collection.last_collected_item_id if resume else None,
            existing_data=existing_data if resume else None,
        )

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
        minio_client.save_json(all_data, collection.raw_data_filename)

        collection.save()

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
        
        logger.info(f"Collection completed for {plan_id}! Total items: {stats.get('total_items', 0)}")
        
    except Collection.DoesNotExist:
        logger.error(f"Collection {plan_id} not found")
        cancellation_registry.remove(plan_id)
    except CollectionCancelledException as e:
        logger.info(f"Collection {plan_id} was cancelled: {e}")
        cancellation_registry.remove(plan_id)
        # Only clean up MinIO file if the collection was fully deleted (not paused)
        try:
            Collection.objects.get(id=plan_id)
            # Collection still exists (paused) — keep MinIO data
            logger.info(f"Collection {plan_id} was paused, keeping MinIO data")
        except Collection.DoesNotExist:
            # Collection was deleted — clean up MinIO file
            if raw_data_filename:
                try:
                    minio_client.delete_file(raw_data_filename)
                    logger.info(f"Final cleanup of MinIO file {raw_data_filename}")
                except Exception as cleanup_error:
                    logger.warning(f"Could not clean up MinIO file during cancellation: {cleanup_error}")
    except Exception as e:
        logger.error(f"Collection failed for {plan_id}: {e}")
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
        except:
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
                    logger.warning(f"Could not publish COLLECTION_FAILED event: {publish_error}")


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
