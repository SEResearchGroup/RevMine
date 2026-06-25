"""Application service orchestrating qualitative dataset lifecycle."""
from __future__ import annotations

import logging
from typing import Optional, Tuple

from quality.models import QualitativeDataset
from quality.tasks import run_build_in_background

logger = logging.getLogger(__name__)


class DatasetService:
    @staticmethod
    def ingest_from_event(payload: dict) -> Optional[QualitativeDataset]:
        """Create/refresh a dataset from a `collection.events.completed` payload
        (only when the collection was flagged for qualitative analysis) and kick
        off the background build."""
        if not payload.get("for_qualitative"):
            return None
        filename = payload.get("qualitative_data_filename")
        collection_id = payload.get("collection_id")
        user_id = payload.get("user_id")
        if not filename or not collection_id or not user_id:
            logger.warning("[Qualitative] Incomplete qualitative collection event: %s", payload)
            return None

        dataset, _ = DatasetService.get_or_create(
            collection_id=collection_id,
            user_id=user_id,
            workspace_id=payload.get("workspace_id"),
            repository_full_name=payload.get("repository_full_name", "") or "",
            platform=payload.get("platform", "") or "",
            qualitative_data_filename=filename,
        )
        # The JSON has just been collected. Leave the dataset "pending" (collected
        # but not prepared) — the user explicitly triggers the build/extraction
        # ("prepare") from the dashboard. Do NOT auto-build here.
        dataset.status = "pending"
        dataset.error_message = None
        dataset.save(update_fields=["status", "error_message", "updated_at"])
        return dataset

    @staticmethod
    def get_or_create(
        collection_id: int,
        user_id: int,
        workspace_id,
        repository_full_name: str,
        platform: str,
        qualitative_data_filename: str,
    ) -> Tuple[QualitativeDataset, bool]:
        dataset = QualitativeDataset.objects.filter(collection_id=collection_id).first()
        created = False
        if dataset is None:
            dataset = QualitativeDataset.objects.create(
                collection_id=collection_id,
                user_id=user_id,
                workspace_id=workspace_id,
                repository_full_name=repository_full_name,
                platform=platform,
                qualitative_data_filename=qualitative_data_filename,
                status="pending",
            )
            created = True
        else:
            dataset.user_id = user_id
            dataset.workspace_id = workspace_id
            dataset.repository_full_name = repository_full_name or dataset.repository_full_name
            dataset.platform = platform or dataset.platform
            dataset.qualitative_data_filename = qualitative_data_filename
            dataset.save()
        return dataset, created

    @staticmethod
    def trigger_build(dataset: QualitativeDataset) -> QualitativeDataset:
        dataset.status = "pending"
        dataset.error_message = None
        dataset.save(update_fields=["status", "error_message", "updated_at"])
        run_build_in_background(str(dataset.id))
        return dataset
