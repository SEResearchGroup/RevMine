from rest_framework import serializers

from quality.models import QualitativeDataset, Comment

_EXCERPT_LEN = 280
_DIFF_PREVIEW_LEN = 400


class QualitativeDatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualitativeDataset
        fields = [
            "id", "collection_id", "repository_full_name", "platform",
            "status", "stats", "error_message", "created_at", "built_at",
        ]


class ReactionSerializer(serializers.Serializer):
    content = serializers.CharField()
    user = serializers.CharField()


class CommentCardSerializer(serializers.ModelSerializer):
    """Compact representation for the horizontal cards / list view."""

    body_excerpt = serializers.SerializerMethodField()
    body_truncated = serializers.SerializerMethodField()
    diff_hunk_preview = serializers.SerializerMethodField()
    has_more_diff = serializers.SerializerMethodField()
    reactions_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id", "review_number", "comment_type", "author", "author_role",
            "author_is_bot", "is_human", "body_excerpt", "body_truncated",
            "path", "line", "side", "diff_hunk_preview", "has_more_diff", "reply_to_id",
            "created_at", "updated_at", "is_resolved", "got_reply",
            "code_changed_after", "reactions_count",
        ]

    def get_body_excerpt(self, obj):
        return (obj.body or "")[:_EXCERPT_LEN]

    def get_body_truncated(self, obj):
        return len(obj.body or "") > _EXCERPT_LEN

    def get_diff_hunk_preview(self, obj):
        return (obj.diff_hunk or "")[:_DIFF_PREVIEW_LEN]

    def get_has_more_diff(self, obj):
        return len(obj.diff_hunk or "") > _DIFF_PREVIEW_LEN

    def get_reactions_count(self, obj):
        return obj.reactions.count()


class CommentDetailSerializer(serializers.ModelSerializer):
    """Full unit for the dedicated detail page: comment + thread + context."""

    reactions = ReactionSerializer(many=True, read_only=True)
    review = serializers.SerializerMethodField()
    thread = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id", "review_number", "comment_type", "author", "author_role",
            "author_is_bot", "is_human", "is_system", "body", "path", "line", "side",
            "diff_hunk", "reply_to_id", "created_at", "updated_at", "is_resolved",
            "got_reply", "code_changed_after", "reactions", "review", "thread",
        ]

    def get_review(self, obj):
        r = obj.review
        return {
            "number": r.number, "title": r.title, "author": r.author,
            "reviewers": r.reviewers, "state": r.state, "url": r.url,
            "additions": r.additions, "deletions": r.deletions,
            "changed_files": r.changed_files,
            "created_at": r.created_at, "merged_at": r.merged_at, "closed_at": r.closed_at,
        }

    def get_thread(self, obj):
        t = obj.thread
        comments = [
            {
                "id": c.id, "author": c.author, "author_is_bot": c.author_is_bot,
                "is_human": c.is_human, "body": c.body, "created_at": c.created_at,
                "reply_to_id": c.reply_to_id,
            }
            for c in t.comments.all()
        ]
        return {
            "id": t.id, "thread_type": t.thread_type, "path": t.path,
            "is_resolved": t.is_resolved, "is_outdated": t.is_outdated,
            "resolved_by": t.resolved_by, "comments": comments,
        }
