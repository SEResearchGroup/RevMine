export const COLLECTION_FEATURES_CONFIG = [
  { id: "Creation_Date", label: "Creation Date", description: "When the PR/MR was created", category: "Basic Info" },
  { id: "Lead_Time", label: "Lead Time", description: "Time from creation to close/merge (in minutes)", category: "Time Metrics" },
  { id: "#Discussions", label: "Discussions Count", description: "Number of discussion threads or comments", category: "Collaboration" },
  { id: "#Commits", label: "Commits Count", description: "Total number of commits in the PR/MR", category: "Basic Info" },
  { id: "Mean_Time_between_commits", label: "Mean Time Between Commits", description: "Average time between consecutive commits (in seconds)", category: "Time Metrics" },
  { id: "Commiters", label: "Committers List", description: "Set of unique committer names (from git config)", category: "Collaboration" },
  { id: "Commiter_Names", label: "Committer Names", description: "Display names of committers (from git config)", category: "Collaboration" },
  { id: "#UniqueCommiters", label: "Unique Committers", description: "Number of unique people who made commits", category: "Collaboration" },
  { id: "nb_minor_author", label: "Minor Authors", description: "Authors who contributed <5% of commits", category: "Collaboration" },
  { id: "nb_major_author", label: "Major Authors", description: "Authors who contributed \u22655% of commits", category: "Collaboration" },
  { id: "delta_time", label: "Delta Time", description: "Time from project creation to PR/MR creation (in seconds)", category: "Time Metrics" },
  { id: "churn_addition", label: "Churn Additions", description: "Total lines added across all commits", category: "Code Metrics" },
  { id: "churn_deletions", label: "Churn Deletions", description: "Total lines deleted across all commits", category: "Code Metrics" },
  { id: "initial_size", label: "Initial Size", description: "Lines changed in commits before MR/PR creation", category: "Code Metrics" },
  { id: "hist_entropy", label: "Historical Entropy", description: "Shannon entropy of file change distribution (code spread)", category: "Code Metrics" },
  { id: "modified_files", label: "Modified Files", description: "Number of files changed in the PR/MR", category: "Code Metrics" },
  { id: "filetypes", label: "File Types", description: "Number of unique file extensions modified", category: "Code Metrics" },
  { id: "state", label: "State", description: "Current state of PR/MR (open, merged, closed)", category: "Basic Info" },
  { id: "rework_size", label: "Rework Size", description: "Lines changed in commits after first review comment", category: "Code Metrics" },
  { id: "Author", label: "Author", description: "PR/MR author username", category: "Collaboration" },
  { id: "Reviewers", label: "Reviewers List", description: "List of reviewer usernames", category: "Collaboration" },
  { id: "#people", label: "People Count", description: "Total unique people involved (authors, reviewers, discussers)", category: "Collaboration" },
  { id: "#reviewers", label: "Reviewers Count", description: "Number of unique reviewers", category: "Collaboration" },
  { id: "#commiters", label: "Committers Count", description: "Number of unique committers", category: "Collaboration" },
  { id: "#discussionners", label: "Discussers Count", description: "Number of unique users in discussions", category: "Collaboration" },
  { id: "additions", label: "Total Additions", description: "Total lines added in the PR/MR", category: "Code Metrics" },
  { id: "deletions", label: "Total Deletions", description: "Total lines deleted in the PR/MR", category: "Code Metrics" },
  { id: "comments", label: "Comments Count", description: "Total number of comments", category: "Collaboration" },
  // --- Dates ---
  { id: "merged_at", label: "Merged At", description: "Date and time the PR/MR was merged", category: "Basic Info" },
  // --- Code-review time metrics ---
  { id: "first_review_at", label: "First Formal Review At", description: "Date of the first formal review action (submit/approve)", category: "Time Metrics" },
  { id: "first_comment_at", label: "First Comment At", description: "Date of the first review comment or feedback", category: "Time Metrics" },
  { id: "approved_at", label: "Approved At", description: "Date the PR/MR received its final approval", category: "Time Metrics" },
  { id: "pickup_time", label: "Pickup Time (h)", description: "Hours from PR creation to first formal review action", category: "Time Metrics" },
  { id: "time_to_first_review", label: "Time to First Review (h)", description: "Hours from PR creation to first comment or feedback", category: "Time Metrics" },
  { id: "review_duration", label: "Review Duration (h)", description: "Hours from first feedback to merge", category: "Time Metrics" },
  { id: "approval_time", label: "Approval Time (h)", description: "Hours from first review to final approval", category: "Time Metrics" },
  { id: "cycle_time", label: "Cycle Time (h)", description: "Total hours from PR creation to merge", category: "Time Metrics" },
];

export const FEATURE_LABELS = Object.fromEntries(
  COLLECTION_FEATURES_CONFIG.map((feature) => [feature.id, feature.label])
);

export const KEYWORD_FIELD_LABELS = {
  title: "Title",
  description: "Description",
  comments: "Comments",
  commit_message: "Commit Message",
};
