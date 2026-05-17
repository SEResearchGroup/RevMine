import pandas as pd
import pytest

from analytics.domain.analysis import analysis_functions as af


@pytest.fixture
def metrics_df():
    return pd.DataFrame(
        {
            "Creation_Date": ["2024-01-01", "2024-01-15", "bad-date"],
            "#Commits": [2, 4, 1],
            "Lead_Time": ["open", "12", "bad"],
            "#UniqueCommiters": [1, 2, 2],
            "Mean_Time_between_commits": [0, 3.5, 8],
            "churn_addition": [10, 20, 30],
            "churn_deletions": [1, 5, 9],
            "initial_mr_size": [11, 25, 39],
            "#Discussions": [0, 2, 2],
            "#people": [2, 3, 4],
            "#reviewers": [1, 1, 2],
            "#commiters": [1, 2, 2],
            "#discussionners": [0, 1, 2],
            "comments": [0, 3, 3],
            "modified_files": [1, 4, 4],
            "filetypes": [".py", ".py", ".md"],
            "hist_entropy": [0.1, 0.5, 0.9],
            "state": ["opened", "merged", "merged"],
            "rework_size": [0, 3, 6],
            "Project_ID": ["A", "A", "B"],
        }
    )


def test_load_data_parses_existing_date_columns_and_ignores_missing(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("created,value\n2024-01-01,1\ninvalid,2\n", encoding="utf-8")

    df = af.load_data(csv_file, date_columns=["created", "missing"])

    assert pd.api.types.is_datetime64_any_dtype(df["created"])
    assert df["created"].isna().sum() == 1


def test_time_series_functions_return_frontend_payload(metrics_df):
    commits = af.plot_commits_over_time(metrics_df, freq="M")["data"]
    timeline = af.plot_mr_creation_timeline(metrics_df, freq="W")["data"]

    assert commits["type"] == "line"
    assert commits["values"] == [6]
    assert timeline["type"] == "bar"
    assert sum(timeline["values"]) == 2


def test_distribution_functions_filter_and_compute_stats(metrics_df):
    lead = af.plot_lead_time_distribution(metrics_df)["data"]
    commits = af.plot_commits_distribution(metrics_df)["data"]
    commit_time = af.plot_commit_time_analysis(metrics_df)["data"]

    assert lead["values"] == [12.0]
    assert commits["labels"] == [1, 2, 4]
    assert commit_time["values"] == [3.5, 8.0]


def test_churn_size_discussion_and_comment_payloads(metrics_df):
    churn = af.plot_code_churn(metrics_df)["data"]
    scatter = af.plot_churn_scatter(metrics_df)["data"]
    size = af.plot_mr_size_analysis(metrics_df)["data"]
    discussions = af.plot_discussions_analysis(metrics_df)["data"]
    comments = af.plot_comments_analysis(metrics_df)["data"]
    files = af.plot_files_modified(metrics_df)["data"]

    assert churn["type"] == "dual_histogram"
    assert scatter["correlation"]["churn_addition"]["churn_deletions"] == pytest.approx(1.0)
    assert size["values"] == [11, 25, 39]
    assert discussions["values"] == [1, 2]
    assert comments["labels"] == [0, 3]
    assert files["labels"] == [1, 4]


def test_collaboration_and_filetype_payloads(metrics_df):
    commiters = af.plot_commiters_analysis(metrics_df)["data"]
    collaboration = af.plot_collaboration_metrics(metrics_df)["data"]
    filetypes = af.plot_filetypes_distribution(metrics_df)["data"]
    entropy = af.plot_entropy_analysis(metrics_df)["data"]
    states = af.plot_state_distribution(metrics_df)["data"]

    assert commiters["labels"] == [1, 2]
    assert collaboration["people"]["values"] == [1, 1, 1]
    assert filetypes["labels"] == [".py", ".md"]
    assert entropy["stats"]["max"] == pytest.approx(0.9)
    assert states["labels"] == ["merged", "opened"]


def test_rework_correlation_complexity_and_project_comparison(metrics_df):
    rework = af.plot_rework_analysis(metrics_df)["data"]
    corr = af.plot_correlation_matrix(metrics_df, columns=["#Commits", "modified_files"])["data"]
    complexity = af.analyze_mr_complexity(metrics_df.copy())["data"]
    project = af.plot_project_comparison(metrics_df)["data"]

    assert rework["values"] == [3, 6]
    assert rework["rework_percentage"] == pytest.approx(66.6666666667)
    assert corr["labels"] == ["#Commits", "modified_files"]
    assert complexity["complexity_scores"] == [5, 13, 11]
    assert project["projects"] == ["A", "B"]
    assert project["sum"] == [6, 1]
