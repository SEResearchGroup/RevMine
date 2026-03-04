#!/usr/bin/env python3
"""Generate 200 training/validation scenarios for the LLM fine-tuning.
User has ALREADY selected the repo — prompts never say "my repo" / "my GitHub".
Platform is inferred from context or defaults to github.
Mix of short/long prompts, French/English, varied filters.
"""

import csv, json

scenarios = []

def add(prompt, output):
    scenarios.append({"input": prompt, "expected_output": json.dumps(output, ensure_ascii=False)})

# Helper for default collect skeleton
def collect(platform, branch, metrics, basic_filters, cleaning_filters, features):
    return {
        "intent": "collect",
        "platform": platform,
        "branch": branch,
        "metrics": metrics,
        "basic_filters": basic_filters,
        "cleaning_filters": cleaning_filters,
        "features": features
    }

def bf(date_range=None, pr_status=None):
    return {"date_range": date_range, "pr_status": pr_status or ["open","closed","merged"]}

def cf(refined=None, ext=None, authors=None, kw_fields=None, kw_terms=None):
    return {
        "refined_date_range": refined,
        "file_extensions": ext or [],
        "authors": authors or [],
        "keywords": {"fields": kw_fields or [], "terms": kw_terms or []}
    }

def analyze(metrics, viz, date_range=None, repos=None, authors=None):
    return {
        "intent": "analyze",
        "metrics": metrics,
        "dimensions": [],
        "filters": {"date_range": date_range, "repositories": repos or [], "authors": authors or []},
        "visualization": viz
    }

# =============================================================================
# 1-10: Very short prompts — minimal input (EN)
# =============================================================================

add("Collect all PRs",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","close_date"],
        bf(), cf(), []))

add("Get commits",
    collect("github", "main",
        ["commit_sha","commit_messages","commit_authors","commit_dates"],
        bf(), cf(), []))

add("Fetch merge requests",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","close_date"],
        bf(), cf(), []))

add("Collect reviews",
    collect("github", "main",
        ["review_state","reviewer","review_date","review_comments","pr_number","pr_title"],
        bf(), cf(), []))

add("Get PR comments",
    collect("github", "main",
        ["pr_comments","comment_authors","comment_dates","comment_content","pr_number","pr_title"],
        bf(), cf(), []))

add("Collect file changes",
    collect("github", "main",
        ["file_names","file_status","lines_added","lines_deleted","total_changes","pr_number"],
        bf(), cf(), []))

add("Calculate lead time",
    collect("github", "main",
        ["creation_date","merge_date","pr_state"],
        bf(), cf(), ["lead_time"]))

add("Get code churn",
    collect("github", "main",
        ["lines_added","lines_deleted","file_names","file_status","pr_number"],
        bf(), cf(), ["churn_additions","churn_deletions"]))

add("Show commits over time",
    analyze(["commits_over_time"], "line_chart"))

add("Visualize state distribution",
    analyze(["state_distribution"], "pie_chart"))

# =============================================================================
# 11-20: Very short prompts — minimal input (FR)
# =============================================================================

add("Récupérer les PRs",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","close_date"],
        bf(), cf(), []))

add("Collecter les commits",
    collect("github", "main",
        ["commit_sha","commit_messages","commit_authors","commit_dates"],
        bf(), cf(), []))

add("Récupérer les merge requests",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","close_date"],
        bf(), cf(), []))

add("Récupérer les reviews",
    collect("github", "main",
        ["review_state","reviewer","review_date","review_comments","pr_number","pr_title"],
        bf(), cf(), []))

add("Collecter les commentaires",
    collect("github", "main",
        ["pr_comments","comment_authors","comment_dates","comment_content","pr_number","pr_title"],
        bf(), cf(), []))

add("Récupérer les changements de fichiers",
    collect("github", "main",
        ["file_names","file_status","lines_added","lines_deleted","total_changes","pr_number"],
        bf(), cf(), []))

add("Calculer le lead time",
    collect("github", "main",
        ["creation_date","merge_date","pr_state"],
        bf(), cf(), ["lead_time"]))

add("Analyser le code churn",
    collect("github", "main",
        ["lines_added","lines_deleted","file_names","file_status","pr_number"],
        bf(), cf(), ["churn_additions","churn_deletions"]))

add("Afficher les commits dans le temps",
    analyze(["commits_over_time"], "line_chart"))

add("Voir la répartition des états",
    analyze(["state_distribution"], "pie_chart"))

# =============================================================================
# 21-35: Medium prompts — single filter (date range)
# =============================================================================

add("Collect PRs from the last month",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf({"start_date":"2026-02-04","end_date":"2026-03-04"}), cf(), []))

add("Get merge requests created in January 2026",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date"],
        bf({"start_date":"2026-01-01","end_date":"2026-01-31"}), cf(), []))

add("Fetch commits from Q4 2025",
    collect("github", "main",
        ["commit_sha","commit_messages","commit_authors","commit_dates"],
        bf({"start_date":"2025-10-01","end_date":"2025-12-31"}), cf(), []))

add("Récupérer les PRs depuis janvier 2025",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf({"start_date":"2025-01-01","end_date":"2026-03-04"}), cf(), []))

add("Collect data from the past 2 weeks",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf({"start_date":"2026-02-18","end_date":"2026-03-04"}), cf(), []))

add("Get PRs between March and August 2025",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf({"start_date":"2025-03-01","end_date":"2025-08-31"}), cf(), []))

add("Récupérer les données des 6 derniers mois",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","close_date"],
        bf({"start_date":"2025-09-04","end_date":"2026-03-04"}), cf(), []))

add("Collect MRs from 2024",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","close_date"],
        bf({"start_date":"2024-01-01","end_date":"2024-12-31"}), cf(), []))

add("Get PRs from this year",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf({"start_date":"2026-01-01","end_date":"2026-03-04"}), cf(), []))

add("Récupérer les MRs du premier semestre 2025",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date"],
        bf({"start_date":"2025-01-01","end_date":"2025-06-30"}), cf(), []))

add("Fetch data from last week",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf({"start_date":"2026-02-25","end_date":"2026-03-04"}), cf(), []))

add("Collecter les MRs de février 2026",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date"],
        bf({"start_date":"2026-02-01","end_date":"2026-02-28"}), cf(), []))

add("Collect PRs from Q1 2026",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf({"start_date":"2026-01-01","end_date":"2026-03-31"}), cf(), []))

add("Get commits from the last 3 months",
    collect("github", "main",
        ["commit_sha","commit_messages","commit_authors","commit_dates"],
        bf({"start_date":"2025-12-04","end_date":"2026-03-04"}), cf(), []))

add("Récupérer les données du dernier trimestre",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf({"start_date":"2025-12-04","end_date":"2026-03-04"}), cf(), []))

# =============================================================================
# 36-50: Medium prompts — single filter (branch)
# =============================================================================

add("Collect PRs from develop branch",
    collect("github", "develop",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf(), cf(), []))

add("Get commits from staging",
    collect("github", "staging",
        ["commit_sha","commit_messages","commit_authors","commit_dates"],
        bf(), cf(), []))

add("Fetch MRs from release branch",
    collect("gitlab", "release",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date"],
        bf(), cf(), []))

add("Collect data from feature/auth",
    collect("github", "feature/auth",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_messages","commit_authors","commit_dates"],
        bf(), cf(), []))

add("Récupérer les MRs depuis la branche hotfix",
    collect("gitlab", "hotfix",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date"],
        bf(), cf(), []))

add("Get PRs from master",
    collect("github", "master",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf(), cf(), []))

add("Collect from production branch",
    collect("gitlab", "production",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","merged_by"],
        bf(), cf(), []))

add("Fetch data from feature/new-ui",
    collect("github", "feature/new-ui",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","file_names","file_status","lines_added","lines_deleted"],
        bf(), cf(), []))

add("Récupérer les données de la branche dev",
    collect("github", "dev",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_messages","commit_authors","commit_dates"],
        bf(), cf(), []))

add("Collect from bugfix/login branch",
    collect("github", "bugfix/login",
        ["commit_sha","commit_messages","commit_authors","commit_dates","file_changes"],
        bf(), cf(), []))

add("Get data from v2.0 branch",
    collect("gitlab", "v2.0",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","commit_id","commit_messages","commit_authors","commit_dates"],
        bf(), cf(), []))

add("Récupérer depuis la branche testing",
    collect("gitlab", "testing",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date"],
        bf(), cf(), []))

add("Collect from integration branch",
    collect("gitlab", "integration",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date"],
        bf(), cf(), []))

add("Get PRs from feature/payment",
    collect("github", "feature/payment",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf(), cf(), []))

add("Fetch from feature/api-v2 branch",
    collect("github", "feature/api-v2",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_messages","commit_authors","commit_dates"],
        bf(), cf(), []))

# =============================================================================
# 51-65: Medium prompts — single filter (status or file ext or author)
# =============================================================================

add("Get only merged PRs",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","merged_by"],
        bf(pr_status=["merged"]), cf(), []))

add("Collect open PRs only",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date"],
        bf(pr_status=["open"]), cf(), []))

add("Récupérer uniquement les MRs fermées",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","creation_date","close_date"],
        bf(pr_status=["closed"]), cf(), []))

add("Collect PRs for Python files only",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","file_names","file_status","lines_added","lines_deleted"],
        bf(), cf(ext=["py"]), []))

add("Get data filtered to JavaScript and TypeScript files",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","creation_date","file_names","file_status","lines_added","lines_deleted"],
        bf(), cf(ext=["js","ts"]), []))

add("Récupérer les données des fichiers Java uniquement",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","creation_date","file_names","file_status","lines_added","lines_deleted"],
        bf(), cf(ext=["java"]), []))

add("Collect data only for .go files",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","creation_date","file_names","file_status","lines_added","lines_deleted"],
        bf(), cf(ext=["go"]), []))

add("Get PRs for CSS and SCSS files",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","file_names","file_status","lines_added","lines_deleted"],
        bf(), cf(ext=["css","scss"]), []))

add("Collect PRs authored by john-dev and sarah-eng",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf(), cf(authors=["john-dev","sarah-eng"]), []))

add("Récupérer les données de l'auteur backend-dev",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf(), cf(authors=["backend-dev"]), []))

add("Get PRs containing 'bugfix' in title",
    collect("github", "main",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date"],
        bf(), cf(kw_fields=["title"], kw_terms=["bugfix"]), []))

add("Collect PRs with 'feature' or 'enhancement' in title",
    collect("github", "main",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date"],
        bf(), cf(kw_fields=["title"], kw_terms=["feature","enhancement"]), []))

add("Récupérer les PRs contenant 'hotfix' dans le titre et la description",
    collect("github", "main",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date"],
        bf(), cf(kw_fields=["title","description"], kw_terms=["hotfix"]), []))

add("Get PRs mentioning 'security' in comments",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","pr_comments","comment_content"],
        bf(), cf(kw_fields=["comments"], kw_terms=["security"]), []))

add("Collect data for .vue and .jsx files",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","creation_date","file_names","file_status","lines_added","lines_deleted"],
        bf(), cf(ext=["vue","jsx"]), []))

# =============================================================================
# 66-85: Feature calculation prompts (EN + FR)
# =============================================================================

add("Calculate lead time and commits count",
    collect("github", "main",
        ["creation_date","merge_date","pr_state","commit_sha","commit_messages","commit_authors","commit_dates"],
        bf(), cf(), ["lead_time","commits_count"]))

add("Compute mean time between commits",
    collect("github", "main",
        ["commit_sha","commit_dates","commit_authors"],
        bf(), cf(), ["mean_time_between_commits"]))

add("I need discussions count and comments count",
    collect("github", "main",
        ["pr_comments","comment_content","comment_authors","pr_number","pr_title"],
        bf(), cf(), ["discussions_count","comments_count"]))

add("Calculate historical entropy",
    collect("github", "main",
        ["file_names","file_changes","file_status"],
        bf(), cf(), ["historical_entropy"]))

add("Get modified files and file types",
    collect("github", "main",
        ["file_names","file_status","lines_added","lines_deleted"],
        bf(), cf(), ["modified_files","file_types"]))

add("Calculate reviewers count",
    collect("github", "main",
        ["reviewer","review_state","review_date","pr_number"],
        bf(), cf(), ["reviewers_count"]))

add("Compute total additions and deletions",
    collect("github", "main",
        ["lines_added","lines_deleted","file_names","file_status","pr_number"],
        bf(), cf(), ["total_additions","total_deletions"]))

add("Get minor and major authors analysis",
    collect("github", "main",
        ["commit_sha","commit_authors","commit_dates","lines_added","lines_deleted"],
        bf(), cf(), ["minor_authors","major_authors"]))

add("Calculate rework size and initial size",
    collect("github", "main",
        ["lines_added","lines_deleted","file_names","file_status","commit_sha","commit_dates","pr_state"],
        bf(pr_status=["merged"]), cf(), ["rework_size","initial_size"]))

add("Compute all time metrics",
    collect("github", "main",
        ["creation_date","merge_date","pr_state","commit_sha","commit_dates","commit_authors"],
        bf(), cf(), ["lead_time","mean_time_between_commits","delta_time"]))

add("Calculer le lead time et le code churn",
    collect("github", "main",
        ["creation_date","merge_date","pr_state","lines_added","lines_deleted","file_names","file_status"],
        bf(), cf(), ["lead_time","churn_additions","churn_deletions"]))

add("Calculer le nombre de commits et le temps moyen entre commits",
    collect("gitlab", "main",
        ["commit_id","commit_dates","commit_authors","commit_messages"],
        bf(), cf(), ["commits_count","mean_time_between_commits"]))

add("Je veux le nombre de reviewers et de discussers",
    collect("github", "main",
        ["reviewer","review_state","review_date","pr_comments","comment_authors","comment_content","pr_number"],
        bf(), cf(), ["reviewers_count","discussers_count"]))

add("Calculer l'entropie historique des fichiers",
    collect("github", "main",
        ["file_names","file_changes","file_status"],
        bf(), cf(), ["historical_entropy"]))

add("Calculate people count and unique committers",
    collect("github", "main",
        ["commit_sha","commit_authors","commit_dates","pr_comments","comment_authors","reviewer","pr_number"],
        bf(), cf(), ["people_count","unique_committers"]))

add("Compute all collaboration metrics",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","commit_sha","commit_authors","commit_dates","pr_comments","comment_authors","comment_content","reviewer","review_state","review_date"],
        bf(), cf(), ["discussions_count","committers_list","unique_committers","committers_count","comments_count","people_count","reviewers_count","discussers_count"]))

add("Obtenir la liste des committers et le nombre d'auteurs",
    collect("gitlab", "main",
        ["commit_id","commit_authors","commit_dates"],
        bf(), cf(), ["committers_list","unique_committers","committers_count"]))

add("Calculate delta time for merged PRs",
    collect("github", "main",
        ["creation_date","merge_date","pr_state"],
        bf(pr_status=["merged"]), cf(), ["delta_time"]))

add("Je veux calculer toutes les métriques de code",
    collect("github", "main",
        ["file_names","file_status","lines_added","lines_deleted","file_changes","commit_sha","commit_dates","pr_state","creation_date","merge_date"],
        bf(), cf(), ["churn_additions","churn_deletions","initial_size","rework_size","total_additions","total_deletions","modified_files","file_types","historical_entropy"]))

add("Compute committers list and count from develop",
    collect("gitlab", "develop",
        ["commit_id","commit_authors","commit_dates"],
        bf(), cf(), ["committers_list","unique_committers","committers_count"]))

# =============================================================================
# 86-110: Combined filters — medium to long prompts (EN + FR)
# =============================================================================

add("Collect merged PRs from develop branch in Q1 2026 for Python files",
    collect("github", "develop",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","file_names","file_status","lines_added","lines_deleted"],
        bf({"start_date":"2026-01-01","end_date":"2026-03-31"}, ["merged"]),
        cf(ext=["py"]), []))

add("Get closed MRs from last month by author devops-user",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","close_date"],
        bf({"start_date":"2026-02-04","end_date":"2026-03-04"}, ["closed"]),
        cf(authors=["devops-user"]), []))

add("Fetch open PRs from staging containing 'WIP' in title",
    collect("github", "staging",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date"],
        bf(pr_status=["open"]),
        cf(kw_fields=["title"], kw_terms=["WIP"]), []))

add("Récupérer les PRs mergées des fichiers .ts et .tsx depuis janvier 2026",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","file_names","file_status","lines_added","lines_deleted"],
        bf({"start_date":"2026-01-01","end_date":"2026-03-04"}, ["merged"]),
        cf(ext=["ts","tsx"]), []))

add("Get merged MRs authored by alice and bob for .py and .js files",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","file_names","lines_added","lines_deleted"],
        bf(pr_status=["merged"]),
        cf(ext=["py","js"], authors=["alice","bob"]), []))

add("Collect PRs from develop in January with 'refactor' keyword in title",
    collect("github", "develop",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date"],
        bf({"start_date":"2026-01-01","end_date":"2026-01-31"}),
        cf(kw_fields=["title"], kw_terms=["refactor"]), []))

add("Récupérer les MRs fermées et mergées par team-lead dans les fichiers .php",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","close_date","old_file_path","new_file_path"],
        bf(pr_status=["closed","merged"]),
        cf(ext=["php"], authors=["team-lead"]), []))

add("Get commits from staging branch in February 2026 for Ruby files",
    collect("github", "staging",
        ["commit_sha","commit_messages","commit_authors","commit_dates","file_changes"],
        bf({"start_date":"2026-02-01","end_date":"2026-02-28"}),
        cf(ext=["rb"]), []))

add("Collect reviews from develop last month",
    collect("github", "develop",
        ["review_state","reviewer","review_date","review_comments","pr_number","pr_title"],
        bf({"start_date":"2026-02-04","end_date":"2026-03-04"}),
        cf(), []))

add("Récupérer les données des fichiers .sql avec le mot 'migration' dans le titre depuis la branche release",
    collect("gitlab", "release",
        ["mr_title","mr_description","mr_iid","mr_state","mr_author","creation_date","old_file_path","new_file_path"],
        bf(),
        cf(ext=["sql"], kw_fields=["title"], kw_terms=["migration"]), []))

add("Get file changes from hotfix branch for .yaml files in Q4 2025",
    collect("github", "hotfix",
        ["file_names","file_status","lines_added","lines_deleted","total_changes","pr_number"],
        bf({"start_date":"2025-10-01","end_date":"2025-12-31"}),
        cf(ext=["yaml","yml"]), []))

add("Collect all MR data from production branch by senior-dev and lead-dev",
    collect("gitlab", "production",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","merged_by","commit_id","commit_messages","commit_authors","commit_dates"],
        bf(),
        cf(authors=["senior-dev","lead-dev"]), []))

add("Récupérer les PRs ouvertes et fermées de la branche develop avec les commentaires",
    collect("github", "develop",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","close_date","pr_comments","comment_authors","comment_dates","comment_content"],
        bf(pr_status=["open","closed"]),
        cf(), []))

add("Get merged PRs with 'deploy' in title for .yml files from staging",
    collect("github", "staging",
        ["pr_title","pr_description","pr_number","pr_state","creation_date","merge_date"],
        bf(pr_status=["merged"]),
        cf(ext=["yml"], kw_fields=["title"], kw_terms=["deploy"]), []))

add("Collect MRs from develop branch in February 2026, only .vue files by frontend-dev",
    collect("gitlab", "develop",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","old_file_path","new_file_path","file_diff"],
        bf({"start_date":"2026-02-01","end_date":"2026-02-28"}),
        cf(ext=["vue"], authors=["frontend-dev"]), []))

add("Fetch PRs from last year mentioning 'performance' in description for .rs files",
    collect("github", "main",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date","file_names","file_status"],
        bf({"start_date":"2025-01-01","end_date":"2025-12-31"}),
        cf(ext=["rs"], kw_fields=["description"], kw_terms=["performance"]), []))

add("Récupérer les PRs des fichiers Kotlin contenant 'fix' ou 'crash' dans le titre",
    collect("github", "main",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date"],
        bf(),
        cf(ext=["kt"], kw_fields=["title"], kw_terms=["fix","crash"]), []))

add("Get PRs filtered to C++ files from develop, open and merged only",
    collect("github", "develop",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","file_names","file_status"],
        bf(pr_status=["open","merged"]),
        cf(ext=["cpp","h"]), []))

add("Collect open PRs from feature/dashboard containing 'WIP' or 'draft' in title",
    collect("github", "feature/dashboard",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date"],
        bf(pr_status=["open"]),
        cf(kw_fields=["title"], kw_terms=["WIP","draft"]), []))

add("Récupérer les données avec une plage de dates raffinée du 1er au 15 février 2026",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf(),
        cf(refined={"start_date":"2026-02-01","end_date":"2026-02-15"}), []))

add("Get merged MRs since January authored by data-engineer for .py and .ipynb files",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","commit_id","commit_authors","commit_dates","old_file_path","new_file_path"],
        bf({"start_date":"2026-01-01","end_date":"2026-03-04"}, ["merged"]),
        cf(ext=["py","ipynb"], authors=["data-engineer"]), []))

add("Collect PRs with 'breaking change' in description from staging in 2025",
    collect("github", "staging",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date","merge_date"],
        bf({"start_date":"2025-01-01","end_date":"2025-12-31"}),
        cf(kw_fields=["description"], kw_terms=["breaking change"]), []))

add("Récupérer les PRs fermées avec le mot 'deprecated' dans les commentaires",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","close_date","pr_comments","comment_content"],
        bf(pr_status=["closed"]),
        cf(kw_fields=["comments"], kw_terms=["deprecated"]), []))

add("Get closed and merged PRs authored by qa-team with 'test' in title",
    collect("github", "main",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date","close_date","merge_date"],
        bf(pr_status=["closed","merged"]),
        cf(authors=["qa-team"], kw_fields=["title"], kw_terms=["test"]), []))

add("Collect MR data from release branch for .swift files author ios-team in 2024",
    collect("gitlab", "release",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","old_file_path","new_file_path","file_diff"],
        bf({"start_date":"2024-01-01","end_date":"2024-12-31"}),
        cf(ext=["swift"], authors=["ios-team"]), []))

# =============================================================================
# 111-140: Long complex prompts — multiple filters + features (EN + FR)
# =============================================================================

add("Collect merged PRs from develop branch in Q1 2026 for Python files and calculate lead time and code churn",
    collect("github", "develop",
        ["creation_date","merge_date","pr_state","pr_title","pr_number","lines_added","lines_deleted","file_names","file_status"],
        bf({"start_date":"2026-01-01","end_date":"2026-03-31"}, ["merged"]),
        cf(ext=["py"]),
        ["lead_time","churn_additions","churn_deletions"]))

add("I want to get all the MR data from release branch, filter by author backend-dev from last month, and calculate discussions count, committers list, and people count",
    collect("gitlab", "release",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","commit_id","commit_authors","commit_dates","discussion_id","discussion_notes","note_content","note_author"],
        bf({"start_date":"2026-02-04","end_date":"2026-03-04"}),
        cf(authors=["backend-dev"]),
        ["discussions_count","committers_list","people_count"]))

add("Fetch merged PRs from staging with 'deploy' in title, for .yaml and .yml files, and compute modified files and file types",
    collect("github", "staging",
        ["pr_title","pr_description","pr_number","pr_state","creation_date","merge_date","file_names","file_status"],
        bf(pr_status=["merged"]),
        cf(ext=["yaml","yml"], kw_fields=["title"], kw_terms=["deploy"]),
        ["modified_files","file_types"]))

add("Collecter les MRs mergées entre janvier et février 2026, calculer le lead time et le nombre de commits",
    collect("gitlab", "main",
        ["mr_title","mr_iid","mr_state","creation_date","merge_date","commit_id","commit_messages","commit_authors","commit_dates"],
        bf({"start_date":"2026-01-01","end_date":"2026-02-28"}, ["merged"]),
        cf(),
        ["lead_time","commits_count"]))

add("Get all PR data with 'API' in title from master branch, only .py and .go files by devops-lead, calculate lead time, commits count, churn and reviewers count",
    collect("github", "master",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_messages","commit_authors","commit_dates","file_names","file_status","lines_added","lines_deleted","reviewer","review_state"],
        bf(),
        cf(ext=["py","go"], authors=["devops-lead"], kw_fields=["title"], kw_terms=["API"]),
        ["lead_time","commits_count","churn_additions","churn_deletions","reviewers_count"]))

add("I need a complete analysis: collect merged PRs from Q4 2025, .ts files only, and calculate all time metrics, code churn, discussions, and committer stats",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_messages","commit_authors","commit_dates","file_names","file_status","lines_added","lines_deleted","file_changes","pr_comments","comment_authors","comment_content","reviewer","review_state","review_date"],
        bf({"start_date":"2025-10-01","end_date":"2025-12-31"}, ["merged"]),
        cf(ext=["ts"]),
        ["lead_time","mean_time_between_commits","delta_time","churn_additions","churn_deletions","discussions_count","committers_list","unique_committers","reviewers_count","comments_count","people_count"]))

add("Collect MR data from develop for .java files with discussion data and calculate historical entropy and file analysis",
    collect("gitlab", "develop",
        ["mr_iid","mr_state","creation_date","old_file_path","new_file_path","file_diff","commit_id","commit_dates","file_changes_diff","discussion_id","discussion_notes"],
        bf(),
        cf(ext=["java"]),
        ["historical_entropy","modified_files","file_types"]))

add("Récupérer les données complètes branche develop, fichiers .py et .yml, par data-engineer, calculer tous les métriques de temps",
    collect("gitlab", "develop",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","commit_id","commit_dates","commit_authors","old_file_path","new_file_path"],
        bf(),
        cf(ext=["py","yml"], authors=["data-engineer"]),
        ["lead_time","mean_time_between_commits","delta_time"]))

add("Get PRs from feature/api-v2 since November 2025, all reviews and inline comments, calculate reviewers count",
    collect("github", "feature/api-v2",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","review_state","reviewer","review_date","review_comments","inline_comments","comment_author","comment_date","code_position","file_path"],
        bf({"start_date":"2025-11-01","end_date":"2026-03-04"}),
        cf(),
        ["reviewers_count"]))

add("Fetch merged MRs from Q4 2025 on release branch by devops and sre-team, calculate total additions and deletions",
    collect("gitlab", "release",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","old_file_path","new_file_path","file_diff"],
        bf({"start_date":"2025-10-01","end_date":"2025-12-31"}, ["merged"]),
        cf(authors=["devops","sre-team"]),
        ["total_additions","total_deletions"]))

add("Collect PRs in February, .ts and .tsx files with 'component' in title, compute lead time, commits count, churn, discussions, and modified files",
    collect("github", "main",
        ["pr_title","pr_description","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_authors","commit_dates","file_names","file_status","lines_added","lines_deleted","pr_comments","comment_content"],
        bf({"start_date":"2026-02-01","end_date":"2026-02-28"}),
        cf(ext=["ts","tsx"], kw_fields=["title"], kw_terms=["component"]),
        ["lead_time","commits_count","churn_additions","churn_deletions","discussions_count","modified_files"]))

add("Récupérer les PRs mergées avec 'optimization' dans les commentaires, fichiers .py, calculer le churn et le rework size",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","creation_date","merge_date","pr_comments","comment_content","file_names","file_status","lines_added","lines_deleted","commit_sha","commit_dates"],
        bf(pr_status=["merged"]),
        cf(ext=["py"], kw_fields=["comments"], kw_terms=["optimization"]),
        ["churn_additions","churn_deletions","rework_size"]))

add("Collect all data from production branch by senior-dev, merged only, compute lead time, delta time, mean time between commits, discussions count, committers list, and people count",
    collect("gitlab", "production",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","commit_id","commit_dates","commit_authors","discussion_id","discussion_notes","note_content","note_author"],
        bf(pr_status=["merged"]),
        cf(authors=["senior-dev"]),
        ["lead_time","delta_time","mean_time_between_commits","discussions_count","committers_list","people_count"]))

add("Collect everything from 2025 for Rust files and calculate all code and time metrics",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_messages","commit_authors","commit_dates","file_names","file_status","lines_added","lines_deleted","file_changes","pr_comments","comment_authors","comment_content","reviewer","review_state","review_date"],
        bf({"start_date":"2025-01-01","end_date":"2025-12-31"}),
        cf(ext=["rs"]),
        ["lead_time","commits_count","mean_time_between_commits","churn_additions","churn_deletions","modified_files","file_types","historical_entropy","discussions_count","committers_list","unique_committers","reviewers_count","comments_count"]))

add("Je veux collecter les PRs fermées et mergées de la branche develop du dernier mois, fichiers .php, par full-stack-dev, et calculer le lead time, discussions count et reviewers count",
    collect("github", "develop",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","close_date","pr_comments","comment_content","comment_authors","reviewer","review_state","review_date"],
        bf({"start_date":"2026-02-04","end_date":"2026-03-04"}, ["closed","merged"]),
        cf(ext=["php"], authors=["full-stack-dev"]),
        ["lead_time","discussions_count","reviewers_count"]))

add("Get MR discussions with notes for merged MRs on integration branch, filter for 'backend' keyword in title, calculate discussions count and comments count",
    collect("gitlab", "integration",
        ["mr_title","mr_description","mr_iid","mr_state","creation_date","merge_date","discussion_id","discussion_notes","resolved_status","note_content","note_author","note_date","note_type"],
        bf(pr_status=["merged"]),
        cf(kw_fields=["title"], kw_terms=["backend"]),
        ["discussions_count","comments_count"]))

add("Collect PRs from feature/notifications this year, .dart files, calculate rework size and initial size",
    collect("github", "feature/notifications",
        ["pr_title","pr_number","pr_state","creation_date","merge_date","commit_sha","commit_dates","file_names","file_status","lines_added","lines_deleted"],
        bf({"start_date":"2026-01-01","end_date":"2026-03-04"}),
        cf(ext=["dart"]),
        ["rework_size","initial_size"]))

add("Récupérer les MRs avec les mots-clés 'CI' et 'pipeline' dans la description, calculer le nombre de commits et la liste des committers",
    collect("gitlab", "main",
        ["mr_title","mr_description","mr_iid","mr_state","mr_author","creation_date","commit_id","commit_messages","commit_authors","commit_dates"],
        bf(),
        cf(kw_fields=["description"], kw_terms=["CI","pipeline"]),
        ["commits_count","mean_time_between_commits","committers_list"]))

add("Get all PR data in 2024 with commits and file changes for .swift files by ios-team, and compute commits count, churn, and modified files",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_messages","commit_authors","commit_dates","file_names","file_status","lines_added","lines_deleted","total_changes"],
        bf({"start_date":"2024-01-01","end_date":"2024-12-31"}),
        cf(ext=["swift"], authors=["ios-team"]),
        ["commits_count","churn_additions","churn_deletions","modified_files"]))

add("Collect data and calculate everything: lead time, code churn, collaboration metrics, file metrics",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_messages","commit_authors","commit_dates","file_names","file_status","lines_added","lines_deleted","file_changes","pr_comments","comment_authors","comment_content","reviewer","review_state","review_date"],
        bf(),
        cf(),
        ["lead_time","commits_count","mean_time_between_commits","delta_time","churn_additions","churn_deletions","initial_size","rework_size","total_additions","total_deletions","modified_files","file_types","historical_entropy","discussions_count","committers_list","unique_committers","minor_authors","major_authors","people_count","reviewers_count","committers_count","discussers_count","comments_count"]))

add("Collecter les MRs de develop entre janvier et février 2026, fichiers .py et .ipynb par ml-engineer, calculer commits count et lead time",
    collect("gitlab", "develop",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","commit_id","commit_messages","commit_authors","commit_dates","old_file_path","new_file_path"],
        bf({"start_date":"2026-01-01","end_date":"2026-02-28"}),
        cf(ext=["py","ipynb"], authors=["ml-engineer"]),
        ["commits_count","lead_time"]))

add("Collect PRs from hotfix branch with refined date range Jan 15 to Feb 15 2026, compute commits and churn",
    collect("github", "hotfix",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_dates","lines_added","lines_deleted","file_names","file_status"],
        bf(),
        cf(refined={"start_date":"2026-01-15","end_date":"2026-02-15"}),
        ["commits_count","churn_additions","churn_deletions"]))

add("Get MR data from v2.0 branch for C# files by dotnet-dev, calculate lead time and total additions, from last quarter",
    collect("gitlab", "v2.0",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","old_file_path","new_file_path","file_diff"],
        bf({"start_date":"2025-12-04","end_date":"2026-03-04"}),
        cf(ext=["cs"], authors=["dotnet-dev"]),
        ["lead_time","total_additions","total_deletions"]))

add("I want commit data and reviews from develop in January for .go files, compute mean time between commits and reviewers count",
    collect("github", "develop",
        ["commit_sha","commit_messages","commit_authors","commit_dates","review_state","reviewer","review_date","review_comments","pr_number","file_names"],
        bf({"start_date":"2026-01-01","end_date":"2026-01-31"}),
        cf(ext=["go"]),
        ["mean_time_between_commits","reviewers_count"]))

add("Fetch MR discussions from testing branch with 'bug' in title, compute discussions count",
    collect("gitlab", "testing",
        ["mr_title","mr_description","mr_iid","mr_state","creation_date","discussion_id","discussion_notes","resolved_status","note_content","note_author"],
        bf(),
        cf(kw_fields=["title"], kw_terms=["bug"]),
        ["discussions_count"]))

add("Récupérer les PRs mergées du Q4 2025 de la branche release, calculer le churn et l'entropie pour les fichiers .scala",
    collect("github", "release",
        ["pr_title","pr_number","pr_state","creation_date","merge_date","file_names","file_status","lines_added","lines_deleted","file_changes"],
        bf({"start_date":"2025-10-01","end_date":"2025-12-31"}, ["merged"]),
        cf(ext=["scala"]),
        ["churn_additions","churn_deletions","historical_entropy"]))

add("Get all data from last 6 months, only .vue and .js files, calculate all collaboration and code metrics",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","commit_sha","commit_messages","commit_authors","commit_dates","file_names","file_status","lines_added","lines_deleted","file_changes","pr_comments","comment_authors","comment_content","reviewer","review_state","review_date"],
        bf({"start_date":"2025-09-04","end_date":"2026-03-04"}),
        cf(ext=["vue","js"]),
        ["lead_time","commits_count","churn_additions","churn_deletions","modified_files","file_types","discussions_count","committers_list","unique_committers","reviewers_count","comments_count","people_count"]))

add("Collecter les MRs ouvertes et fermées de la branche develop du mois dernier, fichiers .php, calculer lead time et discussions",
    collect("gitlab", "develop",
        ["mr_title","mr_iid","mr_state","mr_author","creation_date","merge_date","close_date","discussion_id","discussion_notes","note_content","note_author"],
        bf({"start_date":"2026-02-04","end_date":"2026-03-04"}, ["open","closed"]),
        cf(ext=["php"]),
        ["lead_time","discussions_count"]))

add("Fetch PRs with 'security' or 'vulnerability' in comments, merged only, for .py files, compute lead time and comments count",
    collect("github", "main",
        ["pr_title","pr_number","pr_state","pr_author","creation_date","merge_date","pr_comments","comment_content","comment_authors","file_names"],
        bf(pr_status=["merged"]),
        cf(ext=["py"], kw_fields=["comments"], kw_terms=["security","vulnerability"]),
        ["lead_time","comments_count"]))

# =============================================================================
# 141-160: Analysis scenarios — basic single metric
# =============================================================================

add("Show commits over time",
    analyze(["commits_over_time"], "line_chart"))

add("Visualize lead time distribution",
    analyze(["lead_time_distribution"], "histogram"))

add("Display MR creation timeline",
    analyze(["mr_creation_timeline"], "line_chart"))

add("Show commits distribution",
    analyze(["commits_distribution"], "bar_chart"))

add("Analyze top committers",
    analyze(["commiters_analysis"], "bar_chart"))

add("Show code churn analysis",
    analyze(["code_churn_analysis"], "line_chart"))

add("Display churn scatter",
    analyze(["churn_scatter"], "scatter_plot"))

add("Visualize MR size",
    analyze(["mr_size_analysis"], "histogram"))

add("Show discussions analysis",
    analyze(["discussions_analysis"], "bar_chart"))

add("Display files modified",
    analyze(["files_modified"], "bar_chart"))

add("Afficher l'évolution des commits",
    analyze(["commits_over_time"], "line_chart"))

add("Voir la distribution du lead time",
    analyze(["lead_time_distribution"], "histogram"))

add("Montrer l'analyse du code churn",
    analyze(["code_churn_analysis"], "line_chart"))

add("Afficher la répartition des états",
    analyze(["state_distribution"], "pie_chart"))

add("Visualiser la taille des MR",
    analyze(["mr_size_analysis"], "histogram"))

add("Plot commits over time as a line chart",
    analyze(["commits_over_time"], "line_chart"))

add("Create a bar chart of committers",
    analyze(["commiters_analysis"], "bar_chart"))

add("Generate a scatter plot of churn",
    analyze(["churn_scatter"], "scatter_plot"))

add("Show state distribution as pie chart",
    analyze(["state_distribution"], "pie_chart"))

add("Voir l'analyse des discussions",
    analyze(["discussions_analysis"], "bar_chart"))

# =============================================================================
# 161-180: Analysis with filters (dates, repos, authors)
# =============================================================================

add("Show commits over time from January 2026",
    analyze(["commits_over_time"], "line_chart",
        {"start_date":"2026-01-01","end_date":"2026-01-31"}))

add("Visualize lead time distribution for Q4 2025",
    analyze(["lead_time_distribution"], "histogram",
        {"start_date":"2025-10-01","end_date":"2025-12-31"}))

add("Analyze top committers from last month",
    analyze(["commiters_analysis"], "bar_chart",
        {"start_date":"2026-02-04","end_date":"2026-03-04"}))

add("Show code churn for 2025",
    analyze(["code_churn_analysis"], "line_chart",
        {"start_date":"2025-01-01","end_date":"2025-12-31"}))

add("Display commits distribution by author john-doe",
    analyze(["commits_distribution"], "bar_chart",
        authors=["john-doe"]))

add("Show MR creation timeline for the last 6 months",
    analyze(["mr_creation_timeline"], "line_chart",
        {"start_date":"2025-09-04","end_date":"2026-03-04"}))

add("Visualize files modified in Q1 2026",
    analyze(["files_modified"], "bar_chart",
        {"start_date":"2026-01-01","end_date":"2026-03-31"}))

add("Afficher les discussions du mois dernier",
    analyze(["discussions_analysis"], "bar_chart",
        {"start_date":"2026-02-04","end_date":"2026-03-04"}))

add("Show state distribution for February 2026",
    analyze(["state_distribution"], "pie_chart",
        {"start_date":"2026-02-01","end_date":"2026-02-28"}))

add("Display churn scatter for authors alice and bob from last year",
    analyze(["churn_scatter"], "scatter_plot",
        {"start_date":"2025-01-01","end_date":"2025-12-31"},
        authors=["alice","bob"]))

add("Analyze MR size for frontend-repo in 2025",
    analyze(["mr_size_analysis"], "histogram",
        {"start_date":"2025-01-01","end_date":"2025-12-31"},
        repos=["frontend-repo"]))

add("Show commits over time for backend-api and frontend-app repositories",
    analyze(["commits_over_time"], "line_chart",
        repos=["backend-api","frontend-app"]))

add("Visualiser la distribution des commits par dev-team depuis janvier",
    analyze(["commits_distribution"], "bar_chart",
        {"start_date":"2026-01-01","end_date":"2026-03-04"},
        authors=["dev-team"]))

add("Show lead time for my-project in last quarter",
    analyze(["lead_time_distribution"], "histogram",
        {"start_date":"2025-12-04","end_date":"2026-03-04"},
        repos=["my-project"]))

add("Display code churn by backend-dev in February 2026",
    analyze(["code_churn_analysis"], "line_chart",
        {"start_date":"2026-02-01","end_date":"2026-02-28"},
        authors=["backend-dev"]))

add("Analyze committers for api-service from 2024 to 2025",
    analyze(["commiters_analysis"], "bar_chart",
        {"start_date":"2024-01-01","end_date":"2025-12-31"},
        repos=["api-service"]))

add("Show MR timeline for authors alice, bob, and charlie",
    analyze(["mr_creation_timeline"], "line_chart",
        authors=["alice","bob","charlie"]))

add("Afficher l'analyse des discussions pour mobile-app en 2025",
    analyze(["discussions_analysis"], "bar_chart",
        {"start_date":"2025-01-01","end_date":"2025-12-31"},
        repos=["mobile-app"]))

add("Show files modified for data-pipeline this year",
    analyze(["files_modified"], "bar_chart",
        {"start_date":"2026-01-01","end_date":"2026-03-04"},
        repos=["data-pipeline"]))

add("Visualize state distribution for microservices from August to December 2025",
    analyze(["state_distribution"], "pie_chart",
        {"start_date":"2025-08-01","end_date":"2025-12-31"},
        repos=["microservices"]))

# =============================================================================
# 181-200: Complex multi-metric analysis (EN + FR)
# =============================================================================

add("Show commits distribution and top committers from January",
    analyze(["commits_distribution","commiters_analysis"], "bar_chart",
        {"start_date":"2026-01-01","end_date":"2026-01-31"}))

add("Visualize commits over time and MR creation timeline from last month",
    analyze(["commits_over_time","mr_creation_timeline"], "line_chart",
        {"start_date":"2026-02-04","end_date":"2026-03-04"}))

add("Show code churn and churn scatter for Q4 2025",
    analyze(["code_churn_analysis","churn_scatter"], "scatter_plot",
        {"start_date":"2025-10-01","end_date":"2025-12-31"}))

add("Display lead time distribution and MR size analysis",
    analyze(["lead_time_distribution","mr_size_analysis"], "histogram"))

add("Compare committers and discussions for 2025",
    analyze(["commiters_analysis","discussions_analysis"], "bar_chart",
        {"start_date":"2025-01-01","end_date":"2025-12-31"}))

add("Show commits over time, files modified, and state distribution",
    analyze(["commits_over_time","files_modified","state_distribution"], "bar_chart"))

add("Montrer le churn scatter et la distribution des commits pour backend en janvier",
    analyze(["churn_scatter","commits_distribution"], "scatter_plot",
        {"start_date":"2026-01-01","end_date":"2026-01-31"},
        repos=["backend"]))

add("Analyze MR timeline and discussions for senior-dev and junior-dev",
    analyze(["mr_creation_timeline","discussions_analysis"], "line_chart",
        authors=["senior-dev","junior-dev"]))

add("Visualize code churn, committers, and files modified for my-app in 2025",
    analyze(["code_churn_analysis","commiters_analysis","files_modified"], "bar_chart",
        {"start_date":"2025-01-01","end_date":"2025-12-31"},
        repos=["my-app"]))

add("Show lead time and code churn from the last 3 months by lead-dev",
    analyze(["lead_time_distribution","code_churn_analysis"], "histogram",
        {"start_date":"2025-12-04","end_date":"2026-03-04"},
        authors=["lead-dev"]))

add("Display commits distribution, MR size, and state distribution for multi-repo and api-repo",
    analyze(["commits_distribution","mr_size_analysis","state_distribution"], "bar_chart",
        repos=["multi-repo","api-repo"]))

add("Visualiser l'évolution des commits et les fichiers modifiés ce mois-ci",
    analyze(["commits_over_time","files_modified"], "line_chart",
        {"start_date":"2026-03-01","end_date":"2026-03-04"}))

add("Show committers, discussions, and MR timeline from November 2025 to February 2026",
    analyze(["commiters_analysis","discussions_analysis","mr_creation_timeline"], "bar_chart",
        {"start_date":"2025-11-01","end_date":"2026-02-28"}))

add("Analyze churn scatter and lead time for core-lib by maintainer-1",
    analyze(["churn_scatter","lead_time_distribution"], "scatter_plot",
        repos=["core-lib"], authors=["maintainer-1"]))

add("Afficher la timeline MR et l'analyse du churn pour web-app des 3 derniers mois par fullstack-dev",
    analyze(["mr_creation_timeline","code_churn_analysis"], "line_chart",
        {"start_date":"2025-12-04","end_date":"2026-03-04"},
        repos=["web-app"], authors=["fullstack-dev"]))

add("Compare all metrics: commits, lead time, committers, churn, MR size, discussions, files, state for 2025",
    analyze(["commits_over_time","lead_time_distribution","commiters_analysis","code_churn_analysis","mr_size_analysis","discussions_analysis","files_modified","state_distribution"], "bar_chart",
        {"start_date":"2025-01-01","end_date":"2025-12-31"}))

add("Show commits and code churn by alice from January to February 2026 for frontend-app",
    analyze(["commits_over_time","code_churn_analysis"], "line_chart",
        {"start_date":"2026-01-01","end_date":"2026-02-28"},
        repos=["frontend-app"], authors=["alice"]))

add("Visualiser les discussions et les fichiers modifiés pour le repo api-gateway en Q1 2026",
    analyze(["discussions_analysis","files_modified"], "bar_chart",
        {"start_date":"2026-01-01","end_date":"2026-03-31"},
        repos=["api-gateway"]))

add("Display MR size and state distribution from 2024 for backend-services by devops-team",
    analyze(["mr_size_analysis","state_distribution"], "histogram",
        {"start_date":"2024-01-01","end_date":"2024-12-31"},
        repos=["backend-services"], authors=["devops-team"]))

add("Montrer l'analyse des committers et le churn scatter pour les auteurs alice et bob sur le repo platform en 2025",
    analyze(["commiters_analysis","churn_scatter"], "bar_chart",
        {"start_date":"2025-01-01","end_date":"2025-12-31"},
        repos=["platform"], authors=["alice","bob"]))

add("Show commits over time and MR size for infra-repo authored by sre-lead from Q1 2026",
    analyze(["commits_over_time","mr_size_analysis"], "line_chart",
        {"start_date":"2026-01-01","end_date":"2026-03-31"},
        repos=["infra-repo"], authors=["sre-lead"]))

# =============================================================================
# Write CSV
# =============================================================================
output_path = "/home/s3lf-ouss/pfe/revmine/data/scenarios_llm_200.csv"

with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["input", "expected_output"])
    writer.writeheader()
    for s in scenarios:
        writer.writerow(s)

print(f"Generated {len(scenarios)} scenarios -> {output_path}")

# Stats
import collections
intents = collections.Counter()
langs = {"fr": 0, "en": 0}
lengths = {"short (1-5 words)": 0, "medium (6-15 words)": 0, "long (16+ words)": 0}
platforms = collections.Counter()
branches = collections.Counter()
has_date = 0
has_ext = 0
has_authors = 0
has_keywords = 0
has_features = 0

for s in scenarios:
    o = json.loads(s["expected_output"])
    intents[o["intent"]] += 1
    inp = s["input"]
    fr_words = ["récupérer","collecter","calculer","afficher","voir","montrer","visualiser","je veux","depuis","données","fichiers","branche","dernier","mois","obtenir"]
    if any(w in inp.lower() for w in fr_words):
        langs["fr"] += 1
    else:
        langs["en"] += 1
    wc = len(inp.split())
    if wc <= 5:
        lengths["short (1-5 words)"] += 1
    elif wc <= 15:
        lengths["medium (6-15 words)"] += 1
    else:
        lengths["long (16+ words)"] += 1
    if o["intent"] == "collect":
        platforms[o["platform"]] += 1
        branches[o["branch"]] += 1
        if o["basic_filters"]["date_range"]:
            has_date += 1
        if o["cleaning_filters"]["file_extensions"]:
            has_ext += 1
        if o["cleaning_filters"]["authors"]:
            has_authors += 1
        if o["cleaning_filters"]["keywords"]["terms"]:
            has_keywords += 1
        if o["features"]:
            has_features += 1

print(f"\n{'='*50}")
print(f"STATS")
print(f"{'='*50}")
print(f"Total scenarios: {len(scenarios)}")
print(f"Intents: {dict(intents)}")
print(f"Languages: {langs}")
print(f"Prompt lengths: {lengths}")
print(f"\n--- Collection scenarios ({intents['collect']}) ---")
print(f"Platforms: {dict(platforms)}")
print(f"Unique branches: {len(branches)} -> {dict(branches)}")
print(f"With date filter: {has_date}")
print(f"With file extensions: {has_ext}")
print(f"With author filter: {has_authors}")
print(f"With keywords: {has_keywords}")
print(f"With features: {has_features}")
