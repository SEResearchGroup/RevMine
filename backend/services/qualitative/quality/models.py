import uuid
from django.db import models


class QualitativeDataset(models.Model):
    """A cleaned, structured qualitative dataset built from one qualitative-ready
    collection. Powers the data-exploration dashboard."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("building", "Building"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    collection_id = models.IntegerField(help_text="Source collection id")
    user_id = models.IntegerField()
    workspace_id = models.IntegerField(null=True, blank=True)
    repository_full_name = models.CharField(max_length=500)
    platform = models.CharField(max_length=20)  # "github" | "gitlab"
    qualitative_data_filename = models.CharField(max_length=500)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    stats = models.JSONField(default=dict, help_text="Summary stats for the dashboard header/charts")
    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    built_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "qualitative_datasets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["collection_id"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"QualitativeDataset {self.id} - {self.repository_full_name} ({self.status})"


class Review(models.Model):
    """A pull request (GitHub) or merge request (GitLab)."""

    dataset = models.ForeignKey(QualitativeDataset, on_delete=models.CASCADE, related_name="reviews")
    number = models.IntegerField(help_text="PR number / MR iid")
    title = models.TextField(blank=True, default="")
    body = models.TextField(blank=True, default="")
    author = models.CharField(max_length=255, blank=True, default="")
    reviewers = models.JSONField(default=list)
    state = models.CharField(max_length=40, blank=True, default="")
    url = models.URLField(max_length=1000, blank=True, default="")
    additions = models.IntegerField(null=True, blank=True)
    deletions = models.IntegerField(null=True, blank=True)
    changed_files = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    merged_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "qualitative_reviews"
        ordering = ["-number"]
        indexes = [models.Index(fields=["dataset", "number"])]


class Thread(models.Model):
    GENERAL = "general"
    INLINE = "inline"
    REVIEW_SUMMARY = "review_summary"
    COMMIT_COMMENT = "commit_comment"
    THREAD_TYPES = [
        (GENERAL, "General"),
        (INLINE, "Inline"),
        (REVIEW_SUMMARY, "Review summary"),
        (COMMIT_COMMENT, "Commit comment"),
    ]

    dataset = models.ForeignKey(QualitativeDataset, on_delete=models.CASCADE, related_name="threads")
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="threads")
    external_id = models.CharField(max_length=255, blank=True, default="")
    thread_type = models.CharField(max_length=20, choices=THREAD_TYPES)
    path = models.TextField(blank=True, default="")
    is_resolved = models.BooleanField(null=True, blank=True)
    is_outdated = models.BooleanField(null=True, blank=True)
    resolved_by = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "qualitative_threads"
        indexes = [models.Index(fields=["dataset", "thread_type"])]


class Comment(models.Model):
    """The 'comment unit' — one textual review contribution with its context."""

    dataset = models.ForeignKey(QualitativeDataset, on_delete=models.CASCADE, related_name="comments")
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="comments")
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="comments")

    external_id = models.CharField(max_length=255, blank=True, default="")
    comment_type = models.CharField(max_length=20)  # mirrors thread_type
    author = models.CharField(max_length=255, blank=True, default="")
    # Role of the comment author relative to the PR/MR: "reviewer" (anyone other
    # than the change author) or "author" (the PR/MR author themselves).
    author_role = models.CharField(max_length=10, default="reviewer")
    author_is_bot = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)
    is_human = models.BooleanField(default=True)

    body = models.TextField(blank=True, default="")
    path = models.TextField(blank=True, default="")
    line = models.IntegerField(null=True, blank=True)
    side = models.CharField(max_length=10, blank=True, default="")
    diff_hunk = models.TextField(blank=True, default="")
    reply_to_id = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    # denormalized for cheap filtering/search
    review_number = models.IntegerField(null=True, blank=True)

    # traces
    is_resolved = models.BooleanField(null=True, blank=True)
    got_reply = models.BooleanField(default=False)
    code_changed_after = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "qualitative_comments"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["dataset", "comment_type"]),
            models.Index(fields=["dataset", "author"]),
            models.Index(fields=["dataset", "author_role"]),
            models.Index(fields=["dataset", "is_human"]),
            models.Index(fields=["dataset", "created_at"]),
            models.Index(fields=["dataset", "review_number"]),
        ]


class Reaction(models.Model):
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="reactions")
    content = models.CharField(max_length=100)  # GitHub "content" / GitLab "name"
    user = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "qualitative_reactions"


class Participant(models.Model):
    dataset = models.ForeignKey(QualitativeDataset, on_delete=models.CASCADE, related_name="participants")
    login = models.CharField(max_length=255)
    is_bot = models.BooleanField(default=False)
    comment_count = models.IntegerField(default=0)

    class Meta:
        db_table = "qualitative_participants"
        unique_together = [("dataset", "login")]
