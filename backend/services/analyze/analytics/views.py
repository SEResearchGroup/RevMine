from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.utils import timezone
from django.db import transaction

import pandas as pd
import os
import base64
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt

from .models import Dataset, Analysis, AnalysisResult
from .serializers import (
    DatasetSerializer,
    AnalysisSerializer,
    AnalysisCreateSerializer,
    AnalysisListSerializer,
    AnalysisResultSerializer
)
from .analysis_functions import (
    load_data,
    plot_commits_over_time,
    plot_mr_creation_timeline,
    plot_lead_time_distribution,
    plot_commits_distribution,
    plot_commiters_analysis,
    plot_commit_time_analysis,
    plot_code_churn,
    plot_churn_scatter,
    plot_mr_size_analysis,
    plot_discussions_analysis,
    plot_collaboration_metrics,
    plot_comments_analysis,
    plot_files_modified,
    plot_filetypes_distribution,
    plot_entropy_analysis,
    plot_state_distribution,
    plot_rework_analysis,
    plot_correlation_matrix,
    analyze_mr_complexity,
    plot_project_comparison,
)


class AnalysisCreateView(APIView):
    """
    API endpoint to create a new analysis request
    POST: Upload CSV file and request analysis
    """
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        
        serializer = AnalysisCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        csv_file = serializer.validated_data['csv_file']
        workspace_id = serializer.validated_data.get('workspace_id')
        repository_id = serializer.validated_data.get('repository_id')
        requested_charts = serializer.validated_data['requested_charts']
        try:
            # Save CSV file
            file_path = default_storage.save(
                f'datasets/{csv_file.name}',
                csv_file
            )
            full_path = default_storage.path(file_path)
            
            # Load data to get basic info
            df = pd.read_csv(full_path)
            
            # Create dataset record
            with transaction.atomic():
                dataset = Dataset.objects.create(
                    workspace_id=workspace_id,
                    repository_id=repository_id,
                    filename=csv_file.name,
                    file_path=full_path,
                    rows_count=len(df),
                    columns_count=len(df.columns)
                )
                
                # Create analysis record
                analysis = Analysis.objects.create(
                    dataset=dataset,
                    requested_charts=requested_charts,
                    status='pending'
                )
            self._process_analysis(analysis, full_path, requested_charts)
            
            response_serializer = AnalysisSerializer(analysis)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _process_analysis(self, analysis, file_path, requested_charts):
        """
        Process the analysis and generate charts
        """
        try:
            analysis.status = 'processing'
            analysis.save()
            df = load_data(file_path)
            
            chart_functions = {
                'commits_over_time': lambda: plot_commits_over_time(df),
                'mr_creation_timeline': lambda: plot_mr_creation_timeline(df, "Creation_Date", "W"),
                'lead_time_distribution': lambda: plot_lead_time_distribution(df),
                'commits_distribution': lambda: plot_commits_distribution(df),
                'commiters_analysis': lambda: plot_commiters_analysis(df), 
                'commit_time_analysis': lambda: plot_commit_time_analysis(df),
                'code_churn': lambda: plot_code_churn(df),
                'churn_scatter': lambda: plot_churn_scatter(df),
                'mr_size_analysis': lambda: plot_mr_size_analysis(df),
                'discussions_analysis': lambda: plot_discussions_analysis(df),
                'collaboration_metrics': lambda: plot_collaboration_metrics(df),
                'comments_analysis': lambda: plot_comments_analysis(df),
                'files_modified': lambda: plot_files_modified(df),
                'filetypes_distribution': lambda: plot_filetypes_distribution(df),
                'entropy_analysis': lambda: plot_entropy_analysis(df),
                'state_distribution': lambda: plot_state_distribution(df),
                'rework_analysis': lambda: plot_rework_analysis(df),
                'correlation_matrix': lambda: plot_correlation_matrix(df),
                'mr_complexity': lambda: analyze_mr_complexity(df),
                'project_comparison': lambda: plot_project_comparison(df),
            }
            
            # Generate each requested chart
            print("Starting chart generation")
            print(f"Requested charts: {len(requested_charts)}")
            for chart_type in requested_charts:
                if chart_type in chart_functions:
                    try:
                        print(f"Generating chart: {chart_type}")
                        # Execute the chart function
                        chart_functions[chart_type]()
                        
                        # Convert plot to base64 image
                        buffer = BytesIO()
                        plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
                        buffer.seek(0)
                        image_base64 = base64.b64encode(buffer.read()).decode()
                        plt.close()
                        
                        # Save result
                        AnalysisResult.objects.create(
                            analysis=analysis,
                            chart_type=chart_type,
                            chart_image=image_base64
                        )
                        
                    except Exception as chart_error:
                        # Log chart-specific error but continue
                        print(f"Error generating {chart_type}: {str(chart_error)}")
                        continue
            print("Chart generation completed")
            print(f"Total charts generated: {AnalysisResult.objects.filter(analysis=analysis).count()}")
            analysis.status = 'completed'
            analysis.completed_at = timezone.now()
            analysis.save()
            
        except Exception as e:
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.save()


class AnalysisListView(APIView):
    """
    API endpoint to list all analyses
    GET: List all analyses with optional filtering
    """
    def get(self, request):
        analyses = Analysis.objects.all()
        
        # Filter by workspace_id
        workspace_id = request.query_params.get('workspace_id')
        if workspace_id:
            analyses = analyses.filter(dataset__workspace_id=workspace_id)
        
        # Filter by repository_id
        repository_id = request.query_params.get('repository_id')
        if repository_id:
            analyses = analyses.filter(dataset__repository_id=repository_id)
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            analyses = analyses.filter(status=status_filter)
        
        serializer = AnalysisListSerializer(analyses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AnalysisDetailView(APIView):
    """
    API endpoint to retrieve, update, or delete a specific analysis
    GET: Retrieve analysis details with results
    DELETE: Delete an analysis and its related data
    """
    def get(self, request, analysis_id):
        analysis = get_object_or_404(Analysis, id=analysis_id)
        serializer = AnalysisSerializer(analysis)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request, analysis_id):
        analysis = get_object_or_404(Analysis, id=analysis_id)
        
        # Delete associated dataset file
        try:
            if analysis.dataset.file_path and os.path.exists(analysis.dataset.file_path):
                os.remove(analysis.dataset.file_path)
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
        
        # Delete analysis (cascade will delete results and dataset)
        analysis.delete()
        
        return Response(
            {'message': 'Analysis deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


class DatasetListView(APIView):
    """
    API endpoint to list all datasets
    GET: List all datasets with optional filtering
    """
    def get(self, request):
        datasets = Dataset.objects.all()
        
        # Filter by workspace_id
        workspace_id = request.query_params.get('workspace_id')
        if workspace_id:
            datasets = datasets.filter(workspace_id=workspace_id)
        
        # Filter by repository_id
        repository_id = request.query_params.get('repository_id')
        if repository_id:
            datasets = datasets.filter(repository_id=repository_id)
        
        serializer = DatasetSerializer(datasets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DatasetDetailView(APIView):
    """
    API endpoint to retrieve or delete a specific dataset
    GET: Retrieve dataset details
    DELETE: Delete a dataset and its related analyses
    """
    def get(self, request, dataset_id):
        dataset = get_object_or_404(Dataset, id=dataset_id)
        serializer = DatasetSerializer(dataset)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request, dataset_id):
        dataset = get_object_or_404(Dataset, id=dataset_id)
        # Delete file
        try:
            if dataset.file_path and os.path.exists(dataset.file_path):
                os.remove(dataset.file_path)
        except Exception as e:
            print(f"Error deleting file: {str(e)}")
        
        dataset.delete()
        
        return Response(
            {'message': 'Dataset deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


class AnalysisResultDetailView(APIView):
    """
    API endpoint to retrieve a specific analysis result
    GET: Retrieve a single chart result
    """
    def get(self, request, result_id):
        result = get_object_or_404(AnalysisResult, id=result_id)
        serializer = AnalysisResultSerializer(result)
        return Response(serializer.data, status=status.HTTP_200_OK)