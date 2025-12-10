import threading
from datetime import datetime, date
from django.utils import timezone
from .models import CollectionPlan, CollectedData
from .collector import DataCollector
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
    logger.info(f"Started background collection for plan {plan_id}")


def execute_collection_task(plan_id):
    """
    Execute the actual collection task
    This runs in background and updates progress

    """
    try:
        collection_plan = CollectionPlan.objects.get(id=plan_id)
        
        # Update status to in_progress
        collection_plan.status = 'in_progress'
        collection_plan.started_at = timezone.now()
        collection_plan.save()
        
        logger.info(f"Starting collection for plan {plan_id}")
        
        # Initialize collector
        collector = DataCollector(
            platform=collection_plan.platform,
            token=collection_plan.token_encrypted,
            repo_full_name=collection_plan.repository_full_name
        )
        
        # Prepare filters
        filters = collection_plan.filters.copy()
        if filters.get('start_date'):
            filters['start_date'] = date.fromisoformat(filters['start_date'])
        if filters.get('end_date'):
            filters['end_date'] = date.fromisoformat(filters['end_date'])
        
        # Store all collected data organized by metric
        all_data = {}
        stats = {}
        total_collected = 0
        
        # Collect each metric
        for metric in collection_plan.selected_metrics:
            logger.info(f"Collecting {metric}...")
            
            data = collector.collect_metric(metric, filters)
            all_data[metric] = data
            stats[f"{metric}_count"] = len(data)
            
            logger.info(f"Collected {len(data)} items for {metric}")
            
            total_collected += len(data)
            
            # Update progress
            collection_plan.collected_items = total_collected
            collection_plan.save()
        
        # Calculate date range from collected data
        start_date, end_date = calculate_date_range(all_data)
        
        # Store statistics
        collection_plan.stats = {
            **stats,
            'start_date': start_date,
            'end_date': end_date,
            'total_items': total_collected
        }
        collection_plan.total_items = total_collected
        collection_plan.status = 'completed'
        collection_plan.completed_at = timezone.now()
        collection_plan.save()
        
        # Store all collected data in ONE instance
        CollectedData.objects.update_or_create(
            collection_plan=collection_plan,
            defaults={'raw_data': all_data}
        )
        
        logger.info(f"Collection completed for plan {plan_id}! Total items: {total_collected}")
        
    except CollectionPlan.DoesNotExist:
        logger.error(f"Collection plan {plan_id} not found")
    except Exception as e:
        logger.error(f"Collection failed for plan {plan_id}: {e}")
        
        try:
            collection_plan = CollectionPlan.objects.get(id=plan_id)
            collection_plan.status = 'failed'
            collection_plan.error_message = str(e)
            collection_plan.save()
        except:
            pass


def calculate_date_range(all_data):
    """
    Calculate the date range from collected data
    """
    all_dates = []
    
    for metric, items in all_data.items():
        for item in items:
            date_str = item.get('created_at') or item.get('committed_date')
            if date_str:
                try:
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    all_dates.append(date_obj)
                except:
                    pass
    
    if all_dates:
        start = min(all_dates).strftime('%d/%m/%Y')
        end = max(all_dates).strftime('%d/%m/%Y')
        return start, end
    
    return None, None