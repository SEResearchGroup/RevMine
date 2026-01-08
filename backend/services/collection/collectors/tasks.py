import threading
from datetime import datetime, date
from django.utils import timezone
from .models import Collection
from .github_collector import GitHubCollector
from .gitlab_collector import GitLabCollector
from .minio_client import MinIOClient
import logging

logger = logging.getLogger(__name__)


def run_collection_in_background(plan_id, resume=False):
    """Start collection in a separate thread"""
    thread = threading.Thread(target=execute_collection_task, args=(plan_id, resume))
    thread.daemon = True
    thread.start()
    logger.info(f"Started background collection for collection {plan_id} (resume={resume})")


def execute_collection_task(plan_id, resume=False):
    """Execute the actual collection task with incremental saving"""
    minio_client = MinIOClient()
    
    try:
        collection = Collection.objects.get(id=plan_id)
        
        # Update status
        collection.status = 'in_progress'
        if not resume:
            collection.started_at = timezone.now()
            collection.last_collected_item_id = None
        collection.save()
        
        logger.info(f"Starting collection for {plan_id} (resume={resume})")
        
        # Prepare filters
        filters = collection.filters.copy()
        if filters.get('start_date'):
            filters['start_date'] = date.fromisoformat(filters['start_date'])
        if filters.get('end_date'):
            filters['end_date'] = date.fromisoformat(filters['end_date'])
        
        # Load existing data if resuming
        existing_data = {}
        if resume and collection.raw_data_filename:
            existing_data = minio_client.get_json(collection.raw_data_filename) or {}
        
        # Initialize collector with resume capability
        if collection.platform == 'github':
            collector = GitHubCollector(
                token=collection.token_encrypted,
                repo_full_name=collection.repository_full_name,
                branch_name=collection.branch_name
            )
        else:
            collector = GitLabCollector(
                token=collection.token_encrypted,
                repo_full_name=collection.repository_full_name,
                branch_name=collection.branch_name,
                project_id=collection.external_id  # Pass GitLab project ID directly
            )
        
        # Progress callback with incremental saving
        def save_progress(current, total, message="", item_data=None):
            try:
                collection.collected_items = current
                collection.total_items = total
                
                # Save item data incrementally
                if item_data:
                    item_type = 'pull_requests' if collection.platform == 'github' else 'merge_requests'
                    
                    if item_type not in existing_data:
                        existing_data[item_type] = []
                    
                    existing_data[item_type].append(item_data)
                    
                    # Update last collected item
                    item_number = item_data.get('pull_request_number') or item_data.get('merge_request_id')
                    collection.last_collected_item_id = str(item_number)
                    
                    # Save to MinIO after each item
                    if not collection.raw_data_filename:
                        collection.raw_data_filename = minio_client.generate_filename(
                            collection.repository_name,
                            collection.id,
                            'json'
                        )
                    
                    minio_client.save_json(existing_data, collection.raw_data_filename)
                
                collection.save(update_fields=['collected_items', 'total_items', 'last_collected_item_id', 'raw_data_filename'])
                logger.info(f"Progress: {current}/{total} - {message}")
            except Exception as e:
                logger.error(f"Error saving progress: {e}")
        
        # Collect data
        logger.info("Starting data collection...")
        all_data = collector.collect_all_data(
            filters=filters,
            progress_callback=save_progress,
            resume_from=collection.last_collected_item_id if resume else None,
            existing_data=existing_data if resume else None
        )
        
        # Calculate statistics
        stats = calculate_statistics(all_data, collection.platform)
        
        # Update collection
        collection.stats = stats
        collection.total_items = stats.get('total_items', 0)
        collection.status = 'completed'
        collection.completed_at = timezone.now()
        
        # Generate final filename if not set
        if not collection.raw_data_filename:
            collection.raw_data_filename = minio_client.generate_filename(
                collection.repository_name,
                collection.id,
                'json'
            )
        
        # Save final data
        minio_client.save_json(all_data, collection.raw_data_filename)
        
        collection.save()
        
        logger.info(f"Collection completed for {plan_id}! Total items: {stats.get('total_items', 0)}")
        
    except Collection.DoesNotExist:
        logger.error(f"Collection {plan_id} not found")
    except Exception as e:
        logger.error(f"Collection failed for {plan_id}: {e}")
        
        try:
            collection = Collection.objects.get(id=plan_id)
            collection.status = 'paused' if collection.last_collected_item_id else 'failed'
            collection.error_message = str(e)
            collection.paused_at = timezone.now() if collection.last_collected_item_id else None
            collection.save()
        except:
            pass


def calculate_statistics(all_data, platform):
    """Calculate statistics from collected data"""
    stats = {'total_items': 0}
    
    if platform == 'github':
        prs = all_data.get('pull_requests', [])
        stats['pull_requests_count'] = len(prs)
        stats['total_items'] = len(prs)
        
        total_commits = sum(len(pr.get('commits', [])) for pr in prs)
        total_comments = sum(len(pr.get('comments', [])) for pr in prs)
        total_reviews = sum(len(pr.get('reviews', [])) for pr in prs)
        total_review_comments = sum(len(pr.get('review_comments', [])) for pr in prs)
        
        stats['commits_count'] = total_commits
        stats['comments_count'] = total_comments
        stats['reviews_count'] = total_reviews
        stats['review_comments_count'] = total_review_comments
        
        all_dates = []
        for pr in prs:
            if pr.get('details', {}).get('created_at'):
                try:
                    date_obj = datetime.fromisoformat(pr['details']['created_at'].replace('Z', '+00:00'))
                    all_dates.append(date_obj)
                except:
                    pass
        
        if all_dates:
            stats['start_date'] = min(all_dates).strftime('%d/%m/%Y')
            stats['end_date'] = max(all_dates).strftime('%d/%m/%Y')
    
    else:  # GitLab
        mrs = all_data.get('merge_requests', [])
        stats['merge_requests_count'] = len(mrs)
        stats['total_items'] = len(mrs)
        
        total_commits = sum(len(mr.get('commits', [])) for mr in mrs)
        total_notes = sum(len(mr.get('notes', [])) for mr in mrs)
        total_discussions = sum(len(mr.get('discussions', [])) for mr in mrs)
        
        stats['commits_count'] = total_commits
        stats['notes_count'] = total_notes
        stats['discussions_count'] = total_discussions
        
        all_dates = []
        for mr in mrs:
            if mr.get('details', {}).get('created_at'):
                try:
                    date_obj = datetime.fromisoformat(mr['details']['created_at'].replace('Z', '+00:00'))
                    all_dates.append(date_obj)
                except:
                    pass
        
        if all_dates:
            stats['start_date'] = min(all_dates).strftime('%d/%m/%Y')
            stats['end_date'] = max(all_dates).strftime('%d/%m/%Y')
    
    return stats