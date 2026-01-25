
GITHUB_METRICS = {
    "Pull Request Metadata": [
        {"value": "pr_title", "label": "PR Title"},
        {"value": "pr_description", "label": "PR Description"},
        {"value": "pr_number", "label": "PR Number"},
        {"value": "pr_status", "label": "PR Status"},
        {"value": "pr_state", "label": "PR State (open/closed/merged)"},
        {"value": "pr_author", "label": "PR Author"},
        {"value": "pr_creation_date", "label": "Creation Date"},
        {"value": "pr_merge_date", "label": "Merge Date"},
        {"value": "pr_close_date", "label": "Close Date"},
        {"value": "pr_merged_by", "label": "Merged By"},
    ],
    "Commits": [
        {"value": "commit_sha", "label": "Commit SHA"},
        {"value": "commit_message", "label": "Commit Messages"},
        {"value": "commit_author", "label": "Commit Authors"},
        {"value": "commit_date", "label": "Commit Dates"},
        {"value": "commit_changes", "label": "File Changes"},
    ],
    "Comments": [
        {"value": "pr_comments", "label": "PR Discussion Comments"},
        {"value": "pr_comment_author", "label": "Comment Authors"},
        {"value": "pr_comment_date", "label": "Comment Dates"},
        {"value": "pr_comment_body", "label": "Comment Content"},
    ],
    "Reviews": [
        {"value": "review_state", "label": "Review State (approved/changes_requested/commented)"},
        {"value": "review_author", "label": "Reviewer"},
        {"value": "review_date", "label": "Review Date"},
        {"value": "review_body", "label": "Review Comments"},
    ],
    "Review Comments": [
        {"value": "review_comment_body", "label": "Inline Code Comments"},
        {"value": "review_comment_author", "label": "Comment Author"},
        {"value": "review_comment_date", "label": "Comment Date"},
        {"value": "review_comment_position", "label": "Code Position"},
        {"value": "review_comment_path", "label": "File Path"},
    ],
    "Files": [
        {"value": "file_name", "label": "File Names"},
        {"value": "file_status", "label": "File Status (added/modified/deleted)"},
        {"value": "file_additions", "label": "Lines Added"},
        {"value": "file_deletions", "label": "Lines Deleted"},
        {"value": "file_changes", "label": "Total Changes"},
    ],
}

GITLAB_METRICS = {
    "Merge Request Metadata": [
        {"value": "mr_title", "label": "MR Title"},
        {"value": "mr_description", "label": "MR Description"},
        {"value": "mr_iid", "label": "MR IID"},
        {"value": "mr_status", "label": "MR Status"},
        {"value": "mr_state", "label": "MR State (opened/closed/merged)"},
        {"value": "mr_author", "label": "MR Author"},
        {"value": "mr_creation_date", "label": "Creation Date"},
        {"value": "mr_merge_date", "label": "Merge Date"},
        {"value": "mr_close_date", "label": "Close Date"},
        {"value": "mr_merged_by", "label": "Merged By"},
    ],
    "Commits": [
        {"value": "commit_id", "label": "Commit ID"},
        {"value": "commit_message", "label": "Commit Messages"},
        {"value": "commit_author", "label": "Commit Authors"},
        {"value": "commit_date", "label": "Commit Dates"},
        {"value": "commit_changes", "label": "File Changes (Diff)"},
    ],
    "Discussions": [
        {"value": "discussion_id", "label": "Discussion ID"},
        {"value": "discussion_notes", "label": "Discussion Notes"},
        {"value": "discussion_resolved", "label": "Resolved Status"},
    ],
    "Notes": [
        {"value": "note_body", "label": "Note Content"},
        {"value": "note_author", "label": "Note Author"},
        {"value": "note_date", "label": "Note Date"},
        {"value": "note_type", "label": "Note Type"},
    ],
    "Changes": [
        {"value": "change_old_path", "label": "Old File Path"},
        {"value": "change_new_path", "label": "New File Path"},
        {"value": "change_diff", "label": "File Diff"},
        {"value": "change_new_file", "label": "New File"},
        {"value": "change_renamed_file", "label": "Renamed File"},
        {"value": "change_deleted_file", "label": "Deleted File"},
    ],
}


def get_metrics_for_platform(platform):
    """
    Get metrics based on platform, organized by category
    
    Args:
        platform (str): 'github', 'gitlab', or 'gitlab_self'
    
    Returns:
        dict: Metrics organized by category
    """
    if platform == 'github':
        return GITHUB_METRICS
    elif platform in ['gitlab', 'gitlab_self']:
        return GITLAB_METRICS
    else:
        return {}


def get_all_metric_values(platform):
    """
    Get flat list of all metric values for a platform
    
    Args:
        platform (str): Platform name
    
    Returns:
        list: List of all metric values
    """
    metrics = get_metrics_for_platform(platform)
    all_values = []
    
    for category, metric_list in metrics.items():
        all_values.extend([m['value'] for m in metric_list])
    
    return all_values


def get_category_metric_values(platform, category):
    """
    Get all metric values for a specific category
    
    Args:
        platform (str): Platform name
        category (str): Category name
    
    Returns:
        list: List of metric values in the category
    """
    metrics = get_metrics_for_platform(platform)
    
    if category in metrics:
        return [m['value'] for m in metrics[category]]
    
    return []