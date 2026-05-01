import pandas as pd
import numpy as np


def load_data(filepath, date_columns=None):
    """
    Loads CSV data and converts date columns
    """
    df = pd.read_csv(filepath, index_col=False)

    if date_columns:
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def plot_commits_over_time(
    df, date_col="Creation_Date", commit_col="#Commits", freq="M", figsize=(12, 6)
):
    """
    Plot the number of commits over time
    Returns: dict with 'data' and optionally 'image'
    """
    df_copy = df.copy()
    df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors="coerce")
    df_copy = df_copy.dropna(subset=[date_col])
    df_copy["period"] = df_copy[date_col].dt.to_period(freq)

    commits_by_period = df_copy.groupby("period")[commit_col].sum()

    # Prepare data for frontend
    data = {
        "labels": [str(p) for p in commits_by_period.index],
        "values": commits_by_period.values.tolist(),
        "type": "line",
        "title": f"Number of commits over time (aggregated by {freq})",
        "xLabel": "Period",
        "yLabel": "Total number of commits",
    }

    return {"data": data}


def plot_mr_creation_timeline(df, date_col="Creation_Date", freq="W", figsize=(12, 6)):
    """
    Plot the timeline of MR creation
    """
    df_copy = df.copy()
    df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors="coerce")
    df_copy = df_copy.dropna(subset=[date_col])
    df_copy["period"] = df_copy[date_col].dt.to_period(freq)

    mrs_by_period = df_copy.groupby("period").size()

    data = {
        "labels": [str(p) for p in mrs_by_period.index],
        "values": mrs_by_period.values.tolist(),
        "type": "bar",
        "title": f"Number of MRs created per period ({freq})",
        "xLabel": "Period",
        "yLabel": "Number of MRs",
    }

    return {"data": data}


def plot_lead_time_distribution(df, lead_time_col="Lead_Time", figsize=(12, 6)):
    """
    Distribution of Lead Time
    """
    df_filtered = df[df[lead_time_col] != "open"].copy()
    df_filtered[lead_time_col] = pd.to_numeric(
        df_filtered[lead_time_col], errors="coerce"
    )
    df_filtered = df_filtered.dropna(subset=[lead_time_col])

    values = df_filtered[lead_time_col].values.tolist()
    stats = df_filtered[lead_time_col].describe().to_dict()

    data = {
        "values": values,
        "type": "histogram",
        "title": "Lead Time Distribution",
        "xLabel": "Lead Time (hours)",
        "yLabel": "Frequency",
        "stats": stats,
    }

    return {"data": data}


def plot_commits_distribution(df, commit_col="#Commits", figsize=(10, 6)):
    """
    Distribution of the number of commits per MR
    """
    commits_dist = df[commit_col].value_counts().sort_index()

    data = {
        "labels": commits_dist.index.tolist(),
        "values": commits_dist.values.tolist(),
        "type": "bar",
        "title": "Distribution of the number of commits per MR",
        "xLabel": "Number of commits",
        "yLabel": "Number of MRs",
        "stats": df[commit_col].describe().to_dict(),
    }

    return {"data": data}


def plot_commiters_analysis(df, commiters_col="#UniqueCommiters", figsize=(10, 6)):
    """
    Analysis of the number of unique contributors
    """
    commiters_dist = df[commiters_col].value_counts().sort_index()

    data = {
        "labels": commiters_dist.index.tolist(),
        "values": commiters_dist.values.tolist(),
        "type": "bar",
        "title": "Distribution of the number of unique contributors per MR",
        "xLabel": "Number of contributors",
        "yLabel": "Number of MRs",
    }

    return {"data": data}


def plot_commit_time_analysis(
    df, time_col="Mean_Time_between_commits", figsize=(10, 6)
):
    """
    Analysis of the average time between commits
    """
    df_filtered = df[df[time_col] > 0].copy()
    values = df_filtered[time_col].values.tolist()

    data = {
        "values": values,
        "type": "histogram",
        "title": "Distribution of the average time between commits",
        "xLabel": "Average time (hours)",
        "yLabel": "Frequency",
        "stats": df_filtered[time_col].describe().to_dict(),
    }

    return {"data": data}


def plot_code_churn(
    df, additions_col="churn_addition", deletions_col="churn_deletions", figsize=(14, 6)
):
    """
    Code churn analysis (additions and deletions)
    """
    data = {
        "additions": df[additions_col].values.tolist(),
        "deletions": df[deletions_col].values.tolist(),
        "type": "dual_histogram",
        "title": "Code Churn Analysis",
        "stats": {
            "additions": df[additions_col].describe().to_dict(),
            "deletions": df[deletions_col].describe().to_dict(),
        },
    }

    return {"data": data}


def plot_churn_scatter(
    df, additions_col="churn_addition", deletions_col="churn_deletions", figsize=(10, 8)
):
    """
    Scatter plot: additions vs deletions
    """
    data = {
        "x": df[additions_col].values.tolist(),
        "y": df[deletions_col].values.tolist(),
        "type": "scatter",
        "title": "Relationship between additions and deletions",
        "xLabel": "Lines added",
        "yLabel": "Lines deleted",
        "correlation": df[[additions_col, deletions_col]].corr().to_dict(),
    }

    return {"data": data}


def plot_mr_size_analysis(df, size_col="initial_mr_size", figsize=(10, 6)):
    """
    Initial MR size analysis
    """
    values = df[size_col].values.tolist()

    data = {
        "values": values,
        "type": "histogram",
        "title": "Distribution of initial MR size",
        "xLabel": "Size (lines)",
        "yLabel": "Frequency",
        "stats": df[size_col].describe().to_dict(),
    }

    return {"data": data}


def plot_discussions_analysis(df, discussions_col="#Discussions", figsize=(10, 6)):
    """
    Analysis of the number of discussions
    """
    discussions_dist = df[discussions_col].value_counts().sort_index()

    data = {
        "labels": discussions_dist.index.tolist(),
        "values": discussions_dist.values.tolist(),
        "type": "bar",
        "title": "Distribution of Number of Discussions per MR",
        "xLabel": "Number of Discussions",
        "yLabel": "Number of MRs",
        "stats": df[discussions_col].describe().to_dict(),
    }

    return {"data": data}


def plot_collaboration_metrics(
    df,
    people_col="#people",
    reviewers_col="#reviewers",
    commiters_col="#commiters",
    discussionners_col="#discussionners",
    figsize=(14, 10),
):
    """
    Overview of collaboration metrics
    """
    data = {
        "people": {
            "labels": df[people_col].value_counts().sort_index().index.tolist(),
            "values": df[people_col].value_counts().sort_index().values.tolist(),
        },
        "reviewers": {
            "labels": df[reviewers_col].value_counts().sort_index().index.tolist(),
            "values": df[reviewers_col].value_counts().sort_index().values.tolist(),
        },
        "commiters": {
            "labels": df[commiters_col].value_counts().sort_index().index.tolist(),
            "values": df[commiters_col].value_counts().sort_index().values.tolist(),
        },
        "discussionners": {
            "labels": df[discussionners_col].value_counts().sort_index().index.tolist(),
            "values": df[discussionners_col]
            .value_counts()
            .sort_index()
            .values.tolist(),
        },
        "type": "multi_bar",
        "title": "Collaboration Metrics Overview",
    }

    return {"data": data}


def plot_comments_analysis(df, comments_col="comments", figsize=(10, 6)):
    """
    Analysis of the number of comments
    """
    comments_dist = df[comments_col].value_counts().sort_index()

    data = {
        "labels": comments_dist.index.tolist(),
        "values": comments_dist.values.tolist(),
        "type": "bar",
        "title": "Distribution of Number of Comments per MR",
        "xLabel": "Number of Comments",
        "yLabel": "Number of MRs",
        "stats": df[comments_col].describe().to_dict(),
    }

    return {"data": data}


def plot_files_modified(df, files_col="modified_files", figsize=(10, 6)):
    """
    Analysis of the number of modified files
    """
    files_dist = df[files_col].value_counts().sort_index()

    data = {
        "labels": files_dist.index.tolist(),
        "values": files_dist.values.tolist(),
        "type": "bar",
        "title": "Distribution of the number of modified files per MR",
        "xLabel": "Number of files",
        "yLabel": "Number of MRs",
        "stats": df[files_col].describe().to_dict(),
    }

    return {"data": data}


def plot_filetypes_distribution(df, filetypes_col="filetypes", figsize=(10, 6)):
    """
    Distribution of file types
    """
    filetypes_dist = df[filetypes_col].value_counts().head(15)

    data = {
        "labels": filetypes_dist.index.tolist(),
        "values": filetypes_dist.values.tolist(),
        "type": "horizontal_bar",
        "title": "Top 15 modified file types",
        "xLabel": "Number of MRs",
        "yLabel": "File types",
    }

    return {"data": data}


def plot_entropy_analysis(df, entropy_col="hist_entropy", figsize=(10, 6)):
    """
    Historical entropy analysis
    """
    values = df[entropy_col].values.tolist()

    data = {
        "values": values,
        "type": "histogram",
        "title": "Distribution of historical entropy",
        "xLabel": "Entropy",
        "yLabel": "Frequency",
        "stats": df[entropy_col].describe().to_dict(),
    }

    return {"data": data}


def plot_state_distribution(df, state_col="state", figsize=(8, 8)):
    """
    Distribution of MR states
    """
    state_counts = df[state_col].value_counts()

    data = {
        "labels": state_counts.index.tolist(),
        "values": state_counts.values.tolist(),
        "type": "pie",
        "title": "Distribution of MR States",
    }

    return {"data": data}


def plot_rework_analysis(df, rework_col="rework_size", figsize=(10, 6)):
    """
    Analysis of rework size
    """
    df_filtered = df[df[rework_col] > 0].copy()
    values = df_filtered[rework_col].values.tolist()

    data = {
        "values": values,
        "type": "histogram",
        "title": "Distribution of Rework Size (MRs with rework)",
        "xLabel": "Rework Size",
        "yLabel": "Frequency",
        "stats": df_filtered[rework_col].describe().to_dict(),
        "rework_percentage": (len(df_filtered) / len(df) * 100),
    }

    return {"data": data}


def plot_correlation_matrix(df, columns=None, figsize=(12, 10)):
    """
    Correlation matrix between numerical variables
    """
    if columns is None:
        numeric_df = df.select_dtypes(include=[np.number])
    else:
        numeric_df = df[columns]

    correlation = numeric_df.corr()

    data = {
        "matrix": correlation.values.tolist(),
        "labels": correlation.columns.tolist(),
        "type": "heatmap",
        "title": "Correlation Matrix",
    }

    return {"data": data}


def analyze_mr_complexity(
    df,
    commits_col="#Commits",
    files_col="modified_files",
    discussions_col="#Discussions",
    people_col="#people",
    figsize=(12, 8),
):
    """
    Analysis of MR complexity based on several metrics
    """
    df["complexity_score"] = (
        df[commits_col] + df[files_col] + df[discussions_col] + df[people_col]
    )

    data = {
        "complexity_scores": df["complexity_score"].values.tolist(),
        "commits": df[commits_col].values.tolist(),
        "files": df[files_col].values.tolist(),
        "discussions": df[discussions_col].values.tolist(),
        "type": "scatter_multi",
        "title": "MR Complexity Analysis",
        "xLabel": "Complexity Score",
        "yLabel": "Metric Values",
    }

    return {"data": data}


def plot_project_comparison(
    df, project_col="Project_ID", metric_col="#Commits", figsize=(12, 6)
):
    """
    Comparison of a metric between different projects
    """
    project_stats = df.groupby(project_col)[metric_col].agg(["mean", "median", "sum"])

    data = {
        "projects": project_stats.index.tolist(),
        "mean": project_stats["mean"].values.tolist(),
        "median": project_stats["median"].values.tolist(),
        "sum": project_stats["sum"].values.tolist(),
        "type": "grouped_bar",
        "title": f"Project Comparison - {metric_col}",
        "stats": project_stats.to_dict(),
    }

    return {"data": data}
