import threading
from datetime import datetime, date
from django.utils import timezone
from .models import CollectionPlan, CollectedData
from .github_collector import GitHubCollector
from .gitlab_collector import GitLabCollector
import logging

logger = logging.getLogger(__name__)


def run_collection_in_background(plan_id):
    """
    Start collection in a separate thread
    This allows the API to return immediately while collection continues
    """
    thread = threading.Thread(target=execute_collection_task, args=(plan_id,))
    thread.daemon = True
    thread.start()
    logger.info(f"🚀 Started background collection for plan {plan_id}")


def execute_collection_task(plan_id):
    """
    Execute the actual collection task with real data collectors
    """
    try:
        collection_plan = CollectionPlan.objects.get(id=plan_id)
        
        # Update status to in_progress
        collection_plan.status = 'in_progress'
        collection_plan.started_at = timezone.now()
        collection_plan.save()
        
        logger.info(f"📊 Starting collection for plan {plan_id}")
        
        # Prepare filters
        filters = collection_plan.filters.copy()
        if filters.get('start_date'):
            filters['start_date'] = date.fromisoformat(filters['start_date'])
        if filters.get('end_date'):
            filters['end_date'] = date.fromisoformat(filters['end_date'])
        
        # Progress callback function
        def update_progress(current, total, message=""):
            try:
                collection_plan.collected_items = current
                collection_plan.total_items = total
                collection_plan.save(update_fields=['collected_items', 'total_items'])
                logger.info(f"Progress: {current}/{total} - {message}")
            except Exception as e:
                logger.error(f"Error updating progress: {e}")
        
        # Initialize the appropriate collector
        if collection_plan.platform == 'github':
            collector = GitHubCollector(
                token=collection_plan.token_encrypted,
                repo_full_name=collection_plan.repository_full_name,
                branch_name=collection_plan.branch_name
            )
        else:  # GitLab
            collector = GitLabCollector(
                token=collection_plan.token_encrypted,
                repo_full_name=collection_plan.repository_full_name,
                branch_name=collection_plan.branch_name
            )
        
        # Collect all data with progress updates
        logger.info(f"🔍 Starting data collection...")
        all_data = collector.collect_all_data(
            filters=filters,
            progress_callback=update_progress
        )
        
        # Calculate statistics
        stats = calculate_statistics(all_data, collection_plan.platform)
        
        # Store statistics
        collection_plan.stats = stats
        collection_plan.total_items = stats.get('total_items', 0)
        collection_plan.status = 'completed'
        collection_plan.completed_at = timezone.now()
        collection_plan.save()
        
        # Store all collected data in ONE instance
        CollectedData.objects.update_or_create(
            collection_plan=collection_plan,
            defaults={'raw_data': all_data}
        )
        
        logger.info(f"🎉 Collection completed for plan {plan_id}! Total items: {stats.get('total_items', 0)}")
        
    except CollectionPlan.DoesNotExist:
        logger.error(f"❌ Collection plan {plan_id} not found")
    except Exception as e:
        logger.error(f"❌ Collection failed for plan {plan_id}: {e}")
        
        try:
            collection_plan = CollectionPlan.objects.get(id=plan_id)
            collection_plan.status = 'failed'
            collection_plan.error_message = str(e)
            collection_plan.save()
        except:
            pass


def calculate_statistics(all_data, platform):
    """
    Calculate statistics from collected data
    """
    stats = {
        'total_items': 0
    }
    
    if platform == 'github':
        # GitHub statistics
        prs = all_data.get('pull_requests', [])
        stats['pull_requests_count'] = len(prs)
        stats['total_items'] = len(prs)
        
        # Count commits, comments, reviews
        total_commits = 0
        total_comments = 0
        total_reviews = 0
        total_review_comments = 0
        
        all_dates = []
        
        for pr in prs:
            total_commits += len(pr.get('commits', []))
            total_comments += len(pr.get('comments', []))
            total_reviews += len(pr.get('reviews', []))
            total_review_comments += len(pr.get('review_comments', []))
            
            # Collect dates
            if pr.get('details', {}).get('created_at'):
                try:
                    date_obj = datetime.fromisoformat(
                        pr['details']['created_at'].replace('Z', '+00:00')
                    )
                    all_dates.append(date_obj)
                except:
                    pass
        
        stats['commits_count'] = total_commits
        stats['comments_count'] = total_comments
        stats['reviews_count'] = total_reviews
        stats['review_comments_count'] = total_review_comments
        
        # Calculate date range
        if all_dates:
            start = min(all_dates).strftime('%d/%m/%Y')
            end = max(all_dates).strftime('%d/%m/%Y')
            stats['start_date'] = start
            stats['end_date'] = end
    
    else:  # GitLab
        # GitLab statistics
        mrs = all_data.get('merge_requests', [])
        stats['merge_requests_count'] = len(mrs)
        stats['total_items'] = len(mrs)
        
        # Count commits, notes, discussions
        total_commits = 0
        total_notes = 0
        total_discussions = 0
        
        all_dates = []
        
        for mr in mrs:
            total_commits += len(mr.get('commits', []))
            total_notes += len(mr.get('notes', []))
            total_discussions += len(mr.get('discussions', []))
            
            # Collect dates
            if mr.get('details', {}).get('created_at'):
                try:
                    date_obj = datetime.fromisoformat(
                        mr['details']['created_at'].replace('Z', '+00:00')
                    )
                    all_dates.append(date_obj)
                except:
                    pass
        
        stats['commits_count'] = total_commits
        stats['notes_count'] = total_notes
        stats['discussions_count'] = total_discussions
        
        # Calculate date range
        if all_dates:
            start = min(all_dates).strftime('%d/%m/%Y')
            end = max(all_dates).strftime('%d/%m/%Y')
            stats['start_date'] = start
            stats['end_date'] = end
    
    return stats