import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


def load_data(filepath, date_columns=None):
    """
    Loads CSV data and converts date columns
    """
    df = pd.read_csv(filepath, index_col=False)

    if date_columns:
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
    
    return df


def plot_commits_over_time(df, date_col='Creation_Date', commit_col='#Commits', 
                           freq='M', figsize=(12, 6)):
    """
    Plot the number of commits over time
    """
    df_copy = df.copy()
    df_copy['period'] = df_copy[date_col].dt.to_period(freq)

    commits_by_period = df_copy.groupby('period')[commit_col].sum()

    plt.figure(figsize=figsize)
    commits_by_period.plot(kind='line', marker='o')
    plt.title(f'Number of commits over time (aggregated by {freq})', fontsize=14, fontweight='bold')
    plt.xlabel('Period', fontsize=12)
    plt.ylabel('Total number of commits', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

    return commits_by_period


def plot_mr_creation_timeline(df, date_col='Creation_Date', freq='W', figsize=(12, 6)):
    """
    Plot the timeline of MR creation
    """
    df_copy = df.copy()
    df_copy['period'] = df_copy[date_col].dt.to_period(freq)

    mrs_by_period = df_copy.groupby('period').size()

    plt.figure(figsize=figsize)
    mrs_by_period.plot(kind='bar', color='steelblue')
    plt.title(f'Number of MRs created per period ({freq})', fontsize=14, fontweight='bold')
    plt.xlabel('Period', fontsize=12)
    plt.ylabel('Number of MRs', fontsize=12)
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.show()

    return mrs_by_period



def plot_lead_time_distribution(df, lead_time_col='Lead_Time', figsize=(12, 6)):
    """
    Distribution of Lead Time
    """
    df_filtered = df[df[lead_time_col] != 'open'].copy()
    df_filtered[lead_time_col] = pd.to_numeric(df_filtered[lead_time_col], errors='coerce')
    df_filtered = df_filtered.dropna(subset=[lead_time_col])

    fig, axes = plt.subplots(1, 2, figsize=figsize)

    # Histogram
    axes[0].hist(df_filtered[lead_time_col], bins=30, color='skyblue', edgecolor='black')
    axes[0].set_title('Lead Time Distribution', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Lead Time (hours)', fontsize=10)
    axes[0].set_ylabel('Frequency', fontsize=10)
    axes[0].grid(True, alpha=0.3)

    # Box plot
    axes[1].boxplot(df_filtered[lead_time_col], vert=True)
    axes[1].set_title('Lead Time Box Plot', fontsize=12, fontweight='bold')
    axes[1].set_ylabel('Lead Time (hours)', fontsize=10)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    stats = df_filtered[lead_time_col].describe()
    print(f"\nLead Time statistics:\n{stats}")

    return stats

def plot_commits_distribution(df, commit_col='#Commits', figsize=(10, 6)):
    """
    Distribution of the number of commits per MR

    Args:
        df: DataFrame
        commit_col: Name of the commits column
        figsize: Figure size
    """
    plt.figure(figsize=figsize)

    df[commit_col].value_counts().sort_index().plot(kind='bar', color='coral')
    plt.title('Distribution of the number of commits per MR', fontsize=14, fontweight='bold')
    plt.xlabel('Number of commits', fontsize=12)
    plt.ylabel('Number of MRs', fontsize=12)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.show()

    stats = df[commit_col].describe()
    print(f"\nCommit statistics:\n{stats}")

    return stats


def plot_commiters_analysis(df, commiters_col='#UniqueCommiters', figsize=(10, 6)):
    """
    Analysis of the number of unique contributors

    """
    plt.figure(figsize=figsize)

    commiters_dist = df[commiters_col].value_counts().sort_index()
    commiters_dist.plot(kind='bar', color='lightgreen')
    plt.title('Distribution of the number of unique contributors per MR', fontsize=14, fontweight='bold')
    plt.xlabel('Number of contributors', fontsize=12)
    plt.ylabel('Number of MRs', fontsize=12)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.show()

    return commiters_dist


def plot_commit_time_analysis(df, time_col='Mean_Time_between_commits', figsize=(10, 6)):
    """
    Analysis of the average time between commits
    """
    df_filtered = df[df[time_col] > 0].copy()

    plt.figure(figsize=figsize)
    plt.hist(df_filtered[time_col], bins=30, color='mediumpurple', edgecolor='black')
    plt.title('Distribution of the average time between commits', fontsize=14, fontweight='bold')
    plt.xlabel('Average time (hours)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

    stats = df_filtered[time_col].describe()
    print(f"\nStatistics of time between commits:\n{stats}")

    return stats


def plot_code_churn(df, additions_col='churn_addition', deletions_col='churn_deletions', 
                    figsize=(14, 6)):
    """
    Code churn analysis (additions and deletions)
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    # Additions
    axes[0].hist(df[additions_col], bins=30, color='green', alpha=0.7, edgecolor='black')
    axes[0].set_title('Distribution of code additions', fontsize=12, fontweight='bold')
    axes[0].set_xlabel('Number of lines added', fontsize=10)
    axes[0].set_ylabel('Frequency', fontsize=10)
    axes[0].grid(True, alpha=0.3)
    
    # Deletions
    axes[1].hist(df[deletions_col], bins=30, color='red', alpha=0.7, edgecolor='black')
    axes[1].set_title('Distribution of code deletions', fontsize=12, fontweight='bold')
    axes[1].set_xlabel('Number of lines deleted', fontsize=10)
    axes[1].set_ylabel('Frequency', fontsize=10)
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    print(f"\nAdditions statistics:\n{df[additions_col].describe()}")
    print(f"\nDeletions statistics:\n{df[deletions_col].describe()}")


def plot_churn_scatter(df, additions_col='churn_addition', deletions_col='churn_deletions',
                       figsize=(10, 8)):
    """
    Scatter plot: additions vs deletions
    """
    plt.figure(figsize=figsize)
    plt.scatter(df[additions_col], df[deletions_col], alpha=0.5, c='purple')
    plt.title('Relationship between additions and deletions', fontsize=14, fontweight='bold')
    plt.xlabel('Lines added', fontsize=12)
    plt.ylabel('Lines deleted', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    correlation = df[[additions_col, deletions_col]].corr()
    print(f"\nCorrelation between additions and deletions:\n{correlation}")
    
    return correlation


def plot_mr_size_analysis(df, size_col='initial_mr_size', figsize=(10, 6)):
    """
    Initial MR size analysis
    """
    plt.figure(figsize=figsize)
    plt.hist(df[size_col], bins=30, color='orange', edgecolor='black')
    plt.title('Distribution of initial MR size', fontsize=14, fontweight='bold')
    plt.xlabel('Size (lines)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    stats = df[size_col].describe()
    print(f"\nMR size statistics:\n{stats}")
    
    return stats

def plot_discussions_analysis(df, discussions_col='#Discussions', figsize=(10, 6)):
    """
    Analysis of the number of discussions
    """
    plt.figure(figsize=figsize)

    discussions_dist = df[discussions_col].value_counts().sort_index()
    discussions_dist.plot(kind='bar', color='teal')
    plt.title('Distribution of Number of Discussions per MR', fontsize=14, fontweight='bold')
    plt.xlabel('Number of Discussions', fontsize=12)
    plt.ylabel('Number of MRs', fontsize=12)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.show()

    stats = df[discussions_col].describe()
    print(f"\nDiscussion statistics:\n{stats}")

    return stats


def plot_collaboration_metrics(df, people_col='#people', reviewers_col='#reviewers',
                               commiters_col='#commiters', discussionners_col='#discussionners',
                               figsize=(14, 10)):
    """
    Overview of collaboration metrics
    """
    fig, axes = plt.subplots(2, 2, figsize=figsize)

    # People
    df[people_col].value_counts().sort_index().plot(kind='bar', ax=axes[0, 0], color='steelblue')
    axes[0, 0].set_title('Number of People Involved', fontweight='bold')
    axes[0, 0].set_xlabel('Number of People')
    axes[0, 0].set_ylabel('Number of MRs')
    axes[0, 0].grid(True, alpha=0.3, axis='y')

    # Reviewers
    df[reviewers_col].value_counts().sort_index().plot(kind='bar', ax=axes[0, 1], color='coral')
    axes[0, 1].set_title('Number of Reviewers', fontweight='bold')
    axes[0, 1].set_xlabel('Number of Reviewers')
    axes[0, 1].set_ylabel('Number of MRs')
    axes[0, 1].grid(True, alpha=0.3, axis='y')

    # Committers
    df[commiters_col].value_counts().sort_index().plot(kind='bar', ax=axes[1, 0], color='lightgreen')
    axes[1, 0].set_title('Number of Committers', fontweight='bold')
    axes[1, 0].set_xlabel('Number of Committers')
    axes[1, 0].set_ylabel('Number of MRs')
    axes[1, 0].grid(True, alpha=0.3, axis='y')

    # Discussion participants
    df[discussionners_col].value_counts().sort_index().plot(kind='bar', ax=axes[1, 1], color='mediumpurple')
    axes[1, 1].set_title('Number of Discussion Participants', fontweight='bold')
    axes[1, 1].set_xlabel('Number of Participants')
    axes[1, 1].set_ylabel('Number of MRs')
    axes[1, 1].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.show()


def plot_comments_analysis(df, comments_col='comments', figsize=(10, 6)):
    """
    Analysis of the number of comments
    """
    plt.figure(figsize=figsize)

    df[comments_col].value_counts().sort_index().plot(kind='bar', color='salmon')
    plt.title('Distribution of Number of Comments per MR', fontsize=14, fontweight='bold')
    plt.xlabel('Number of Comments', fontsize=12)
    plt.ylabel('Number of MRs', fontsize=12)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.show()

    stats = df[comments_col].describe()
    print(f"\nComment statistics:\n{stats}")

    return stats


def plot_files_modified(df, files_col='modified_files', figsize=(10, 6)):
    """
    Analysis of the number of modified files
    """
    plt.figure(figsize=figsize)

    df[files_col].value_counts().sort_index().plot(kind='bar', color='gold')
    plt.title('Distribution of the number of modified files per MR', fontsize=14, fontweight='bold')
    plt.xlabel('Number of files', fontsize=12)
    plt.ylabel('Number of MRs', fontsize=12)
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.show()

    stats = df[files_col].describe()
    print(f"\nModified files statistics:\n{stats}")

    return stats


def plot_filetypes_distribution(df, filetypes_col='filetypes', figsize=(10, 6)):
    """
    Distribution of file types
    """
    plt.figure(figsize=figsize)

    df[filetypes_col].value_counts().head(15).plot(kind='barh', color='skyblue')
    plt.title('Top 15 modified file types', fontsize=14, fontweight='bold')
    plt.xlabel('Number of MRs', fontsize=12)
    plt.ylabel('File types', fontsize=12)
    plt.grid(True, alpha=0.3, axis='x')
    plt.tight_layout()
    plt.show()



def plot_entropy_analysis(df, entropy_col='hist_entropy', figsize=(10, 6)):
    """
    Historical entropy analysis
    """
    plt.figure(figsize=figsize)
    plt.hist(df[entropy_col], bins=30, color='indigo', edgecolor='black')
    plt.title('Distribution of historical entropy', fontsize=14, fontweight='bold')
    plt.xlabel('Entropy', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

    stats = df[entropy_col].describe()
    print(f"\nEntropy statistics:\n{stats}")

    return stats



def plot_state_distribution(df, state_col='state', figsize=(8, 8)):
    """
    Distribution of MR states
    """
    plt.figure(figsize=figsize)

    state_counts = df[state_col].value_counts()
    colors = plt.cm.Set3(range(len(state_counts)))
    plt.pie(state_counts, labels=state_counts.index, autopct='%1.1f%%', colors=colors, startangle=90)
    plt.title('Distribution of MR States', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()

    print(f"\nNumber of MRs per state:\n{state_counts}")

    return state_counts


def plot_rework_analysis(df, rework_col='rework_size', figsize=(10, 6)):
    """
    Analysis of rework size
    """
    df_filtered = df[df[rework_col] > 0].copy()

    plt.figure(figsize=figsize)
    plt.hist(df_filtered[rework_col], bins=30, color='crimson', edgecolor='black')
    plt.title('Distribution of Rework Size (MRs with rework)', fontsize=14, fontweight='bold')
    plt.xlabel('Rework Size', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

    print(f"\nPercentage of MRs with rework: {len(df_filtered) / len(df) * 100:.2f}%")
    stats = df_filtered[rework_col].describe()
    print(f"\nRework statistics:\n{stats}")

    return stats


def plot_correlation_matrix(df, columns=None, figsize=(12, 10)):
    """
    Correlation matrix between numerical variables
    """
    if columns is None:
        # Select only numerical columns
        numeric_df = df.select_dtypes(include=[np.number])
    else:
        numeric_df = df[columns]

    correlation = numeric_df.corr()

    plt.figure(figsize=figsize)
    sns.heatmap(correlation, annot=True, fmt='.2f', cmap='coolwarm', center=0,
                square=True, linewidths=1, cbar_kws={"shrink": 0.8})
    plt.title('Correlation Matrix', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()

    return correlation


def analyze_mr_complexity(df, commits_col='#Commits', files_col='modified_files',
                         discussions_col='#Discussions', people_col='#people',
                         figsize=(12, 8)):
    """
    Analysis of MR complexity based on several metrics
    """
    # Create a complexity score
    df['complexity_score'] = (
        df[commits_col] +
        df[files_col] +
        df[discussions_col] +
        df[people_col]
    )

    plt.figure(figsize=figsize)
    plt.scatter(df['complexity_score'], df[commits_col], alpha=0.5, c='blue', label='Commits')
    plt.scatter(df['complexity_score'], df[files_col], alpha=0.5, c='red', label='Files')
    plt.scatter(df['complexity_score'], df[discussions_col], alpha=0.5, c='green', label='Discussions')
    plt.title('MR Complexity Analysis', fontsize=14, fontweight='bold')
    plt.xlabel('Complexity Score', fontsize=12)
    plt.ylabel('Metric Values', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

    print("\nTop 10 most complex MRs:")
    print(df.nlargest(10, 'complexity_score')[['MR_ID', 'complexity_score', commits_col,
                                               files_col, discussions_col, people_col]])

    return df['complexity_score']


def plot_project_comparison(df, project_col='Project_ID', metric_col='#Commits', figsize=(12, 6)):
    """
    Comparison of a metric between different projects
    """
    project_stats = df.groupby(project_col)[metric_col].agg(['mean', 'median', 'sum'])

    fig, axes = plt.subplots(1, 3, figsize=figsize)

    project_stats['mean'].plot(kind='bar', ax=axes[0], color='steelblue')
    axes[0].set_title(f'Mean of {metric_col} per project', fontweight='bold')
    axes[0].set_xlabel('Project ID')
    axes[0].set_ylabel('Mean')
    axes[0].grid(True, alpha=0.3, axis='y')

    project_stats['median'].plot(kind='bar', ax=axes[1], color='coral')
    axes[1].set_title(f'Median of {metric_col} per project', fontweight='bold')
    axes[1].set_xlabel('Project ID')
    axes[1].set_ylabel('Median')
    axes[1].grid(True, alpha=0.3, axis='y')

    project_stats['sum'].plot(kind='bar', ax=axes[2], color='lightgreen')
    axes[2].set_title(f'Total of {metric_col} per project', fontweight='bold')
    axes[2].set_xlabel('Project ID')
    axes[2].set_ylabel('Total')
    axes[2].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.show()

    print(f"\nStatistics of {metric_col} per project:\n{project_stats}")

    return project_stats