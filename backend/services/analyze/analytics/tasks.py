from celery import shared_task
from django.utils import timezone
from .analysis_service import AnalysisService
from .models import Analysis

@shared_task
def process_analysis(analysis_id):
    """
    Process a single analysis asynchronously
    """
    
    
    try:
        analysis = Analysis.objects.get(id=analysis_id)
        service = AnalysisService()
        service.process_analysis(analysis)
        
        return {
            'status': 'success',
            'analysis_id': str(analysis_id),
            'message': 'Analysis completed successfully'
        }
        
    except Analysis.DoesNotExist:
        return {
            'status': 'error',
            'analysis_id': str(analysis_id),
            'message': 'Analysis not found'
        }
    except Exception as e:
        return {
            'status': 'error',
            'analysis_id': str(analysis_id),
            'message': str(e)
        }


@shared_task
def process_batch(batch_id):
    """
    Process all analyses in a batch
    """
    from .models import AnalysisBatch
    
    try:
        batch = AnalysisBatch.objects.get(id=batch_id)
        batch.status = 'processing'
        batch.save()
        
        # Process each analysis
        for batch_analysis in batch.batch_analyses.all():
            analysis = batch_analysis.analysis
            
            try:
                service = AnalysisService()
                service.process_analysis(analysis)
                
                batch.completed_analyses += 1
                batch.save()
                
            except Exception as e:
                batch.failed_analyses += 1
                batch.save()
        
        # Update batch status
        if batch.failed_analyses == 0:
            batch.status = 'completed'
        elif batch.completed_analyses > 0:
            batch.status = 'partial'
        else:
            batch.status = 'failed'
        
        batch.completed_at = timezone.now()
        batch.save()
        
        return {
            'status': 'success',
            'batch_id': str(batch_id),
            'completed': batch.completed_analyses,
            'failed': batch.failed_analyses
        }
        
    except AnalysisBatch.DoesNotExist:
        return {
            'status': 'error',
            'batch_id': str(batch_id),
            'message': 'Batch not found'
        }
    except Exception as e:
        return {
            'status': 'error',
            'batch_id': str(batch_id),
            'message': str(e)
        }


@shared_task
def cleanup_old_analyses(days=30):
    """
    Clean up old analyses and their results
    """
    from datetime import timedelta
    from django.utils import timezone
    from .models import Analysis
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Delete old analyses
    deleted_count = Analysis.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['completed', 'failed']
    ).delete()
    
    return {
        'status': 'success',
        'deleted_count': deleted_count[0],
        'message': f'Deleted analyses older than {days} days'
    }