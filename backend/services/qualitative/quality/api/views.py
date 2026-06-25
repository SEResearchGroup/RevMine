from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from quality.models import QualitativeDataset, Comment, Review
from quality.services.dataset_service import DatasetService
from quality.api.serializers import (
    QualitativeDatasetSerializer,
    CommentCardSerializer,
    CommentDetailSerializer,
)


class _UserMixin:
    def get_user_id(self, request):
        return getattr(request, "user_id", None)

    def user_required(self):
        return Response({"error": "X-User-ID header required"}, status=status.HTTP_400_BAD_REQUEST)

    def get_dataset(self, request, dataset_id):
        user_id = self.get_user_id(request)
        return get_object_or_404(QualitativeDataset, id=dataset_id, user_id=user_id)


def _parse_bool(value):
    if value is None:
        return None
    return str(value).lower() in ("1", "true", "yes")


class DatasetListView(_UserMixin, APIView):
    """GET /datasets/ — qualitative-ready datasets for the user (picker)."""

    def get(self, request):
        user_id = self.get_user_id(request)
        if user_id is None:
            return self.user_required()
        qs = QualitativeDataset.objects.filter(user_id=user_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response({"datasets": QualitativeDatasetSerializer(qs, many=True).data})


class DatasetDetailView(_UserMixin, APIView):
    """GET /datasets/<id>/ — project header + stats."""

    def get(self, request, dataset_id):
        if self.get_user_id(request) is None:
            return self.user_required()
        dataset = self.get_dataset(request, dataset_id)
        return Response(QualitativeDatasetSerializer(dataset).data)


class DatasetRebuildView(_UserMixin, APIView):
    """POST /datasets/<id>/rebuild/ — re-run the ETL."""

    def post(self, request, dataset_id):
        if self.get_user_id(request) is None:
            return self.user_required()
        dataset = self.get_dataset(request, dataset_id)
        DatasetService.trigger_build(dataset)
        return Response({"status": "building", "dataset_id": str(dataset.id)})


class CommentListView(_UserMixin, APIView):
    """GET /datasets/<id>/comments/ — paginated, searchable, filterable cards."""

    def get(self, request, dataset_id):
        if self.get_user_id(request) is None:
            return self.user_required()
        dataset = self.get_dataset(request, dataset_id)
        qp = request.query_params

        qs = Comment.objects.filter(dataset=dataset)

        if not _parse_bool(qp.get("include_non_human")):
            qs = qs.filter(is_human=True)

        ctype = qp.get("type") or qp.get("category")
        if ctype:
            qs = qs.filter(comment_type=ctype)

        # Role of the comment author: "reviewer" (default focus of qualitative
        # analysis) vs "author" (the PR/MR author themselves).
        role = qp.get("role")
        if role in ("reviewer", "author"):
            qs = qs.filter(author_role=role)

        author = qp.get("author")
        if author:
            qs = qs.filter(author__iexact=author)

        q = qp.get("q")
        if q:
            qs = qs.filter(body__icontains=q)

        resolved = _parse_bool(qp.get("resolved"))
        if resolved is not None:
            qs = qs.filter(is_resolved=resolved)

        path = qp.get("path")
        if path:
            qs = qs.filter(path__icontains=path)

        review_number = qp.get("review_number")
        if review_number:
            qs = qs.filter(review_number=review_number)

        if qp.get("date_from"):
            qs = qs.filter(created_at__gte=qp.get("date_from"))
        if qp.get("date_to"):
            qs = qs.filter(created_at__lte=qp.get("date_to"))

        qs = qs.order_by("-created_at", "id")

        try:
            page = max(1, int(qp.get("page", 1)))
            page_size = min(100, max(1, int(qp.get("page_size", 20))))
        except ValueError:
            page, page_size = 1, 20

        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        return Response({
            "count": paginator.count,
            "page": page_obj.number,
            "num_pages": paginator.num_pages,
            "results": CommentCardSerializer(page_obj.object_list, many=True).data,
        })


class CommentDetailView(_UserMixin, APIView):
    """GET /datasets/<id>/comments/<comment_id>/ — full unit + thread + context."""

    def get(self, request, dataset_id, comment_id):
        if self.get_user_id(request) is None:
            return self.user_required()
        dataset = self.get_dataset(request, dataset_id)
        comment = get_object_or_404(Comment, id=comment_id, dataset=dataset)
        return Response(CommentDetailSerializer(comment).data)


class FacetsView(_UserMixin, APIView):
    """GET /datasets/<id>/facets/ — distinct values for filter dropdowns,
    split by actor role so the person dropdown can be scoped to reviewers."""

    def get(self, request, dataset_id):
        if self.get_user_id(request) is None:
            return self.user_required()
        dataset = self.get_dataset(request, dataset_id)
        base = Comment.objects.filter(dataset=dataset, is_human=True).order_by()
        reviewers = sorted(
            v for v in base.filter(author_role="reviewer").values_list("author", flat=True).distinct() if v
        )
        authors = sorted(
            v for v in base.filter(author_role="author").values_list("author", flat=True).distinct() if v
        )
        types = sorted(
            v for v in base.values_list("comment_type", flat=True).distinct() if v
        )
        review_numbers = list(
            Review.objects.filter(dataset=dataset).order_by("-number").values_list("number", flat=True)
        )
        return Response({
            "roles": ["reviewer", "author"],
            "reviewers": reviewers,  # people who reviewed others' changes
            "authors": authors,      # PR/MR authors (self-comments)
            "types": types,
            "review_numbers": review_numbers,
        })


class TimeseriesView(_UserMixin, APIView):
    """GET /datasets/<id>/timeseries/?granularity=day|week|month — comment counts
    bucketed over time, honouring the role / non-human filters."""

    TRUNC = {"day": TruncDay, "week": TruncWeek, "month": TruncMonth}

    def get(self, request, dataset_id):
        if self.get_user_id(request) is None:
            return self.user_required()
        dataset = self.get_dataset(request, dataset_id)
        qp = request.query_params

        granularity = qp.get("granularity", "month")
        trunc = self.TRUNC.get(granularity, TruncMonth)

        qs = Comment.objects.filter(dataset=dataset, created_at__isnull=False)
        if not _parse_bool(qp.get("include_non_human")):
            qs = qs.filter(is_human=True)
        role = qp.get("role")
        if role in ("reviewer", "author"):
            qs = qs.filter(author_role=role)

        rows = (
            qs.annotate(period=trunc("created_at"))
            .values("period")
            .annotate(count=Count("id"))
            .order_by("period")
        )
        series = [
            {"period": r["period"].strftime("%Y-%m-%d"), "count": r["count"]}
            for r in rows if r["period"] is not None
        ]
        return Response({"granularity": granularity, "series": series})


class StartAnalysisView(_UserMixin, APIView):
    """POST /datasets/<id>/analyses/ — start the automatic (LLM) analysis.

    Phase A: this is the dashboard CTA target. It validates the dataset is ready
    and returns 'queued'; the LLM judging pipeline is implemented in Phase B.
    """

    def post(self, request, dataset_id):
        if self.get_user_id(request) is None:
            return self.user_required()
        dataset = self.get_dataset(request, dataset_id)
        if dataset.status != "ready":
            return Response(
                {"error": f"Dataset is not ready (status={dataset.status})"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {"status": "queued", "dataset_id": str(dataset.id),
             "detail": "Automatic analysis is not yet available (Phase B)."},
            status=status.HTTP_202_ACCEPTED,
        )
