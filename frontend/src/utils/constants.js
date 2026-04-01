const AVAILABLE_METRICS = [
  {
    id: "commits_over_time",
    label: "Commits Over Time",
    description: "Visualize commit frequency over time",
  },
  {
    id: "mr_creation_timeline",
    label: "MR Creation Timeline",
    description: "Track merge request creation patterns",
  },
  {
    id: "lead_time_distribution",
    label: "Lead Time Distribution",
    description: "Analyze time from commit to merge",
  },
  {
    id: "commits_distribution",
    label: "Commits Distribution",
    description: "Distribution of commits across MRs",
  },
  {
    id: "commiters_analysis",
    label: "Committers Analysis",
    description: "Analyze contributor activity",
  },
  {
    id: "commit_time_analysis",
    label: "Commit Time Analysis",
    description: "When commits are made",
  },
  {
    id: "code_churn",
    label: "Code Churn",
    description: "Lines added vs removed over time",
  },
  {
    id: "churn_scatter",
    label: "Churn Scatter Plot",
    description: "Scatter plot of code changes",
  },
  {
    id: "mr_size_analysis",
    label: "MR Size Analysis",
    description: "Analyze merge request sizes",
  },
  {
    id: "discussions_analysis",
    label: "Discussions Analysis",
    description: "Discussion patterns in MRs",
  },
  {
    id: "collaboration_metrics",
    label: "Collaboration Metrics",
    description: "Team collaboration patterns",
  },
  {
    id: "comments_analysis",
    label: "Comments Analysis",
    description: "Comment patterns and frequency",
  },
  {
    id: "files_modified",
    label: "Files Modified",
    description: "Files changed in MRs",
  },
  {
    id: "filetypes_distribution",
    label: "File Types Distribution",
    description: "Distribution of file types",
  },
  {
    id: "entropy_analysis",
    label: "Entropy Analysis",
    description: "Code complexity analysis",
  },
  {
    id: "state_distribution",
    label: "State Distribution",
    description: "MR state distribution",
  },
  {
    id: "rework_analysis",
    label: "Rework Analysis",
    description: "Code rework patterns",
  },
  {
    id: "correlation_matrix",
    label: "Correlation Matrix",
    description: "Metric correlations",
  },
  {
    id: "mr_complexity",
    label: "MR Complexity",
    description: "Complexity analysis of merge requests",
  },
  {
    id: "project_comparison",
    label: "Project Comparison",
    description: "Compare multiple projects",
  },
];

export { AVAILABLE_METRICS };
