import requests
from datetime import datetime
import logging
import re

from .http_client import create_retry_session

logger = logging.getLogger(__name__)


def _create_session(headers, max_retries=5, backoff_factor=1):
    """Create a requests.Session with retry + exponential backoff."""
    return create_retry_session(
        headers,
        max_retries=max_retries,
        backoff_factor=backoff_factor,
    )


class GitHubCollector:
    """Collects data from GitHub API with resume capability"""
    
    def __init__(self, token, repo_full_name, branch_name=None, selected_metrics=None):
        self.token = token
        self.repo_full_name = repo_full_name
        self.branch_name = branch_name
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.session = _create_session(self.headers)
        self.selected_metrics = selected_metrics
        self.required_endpoints = None  # Computed lazily
        self.for_qualitative = False  # Enables thread-resolution + reactions enrichment
        self.project_created_at = None  # Fetched from API
    
    def collect_all_data(self, filters=None, progress_callback=None, resume_from=None, existing_data=None):
        """
        Collect all pull request data with progress updates and resume support

        Args:
            filters (dict): Date and status filters
            progress_callback (callable): Function to call with progress updates (current, total, message, item_data)
            resume_from (str): PR number to resume from (if resuming)
            existing_data (dict): Existing collected data (if resuming)

        Returns:
            dict: All collected data organized by type
        """
        if existing_data:
            all_data = existing_data
        else:
            all_data = {"pull_requests": []}

        self.is_total_approximate = False

        try:
            # Fetch project creation date
            try:
                repo_response = self.session.get(
                    f"{self.base_url}/repos/{self.repo_full_name}",
                    timeout=30
                )
                if repo_response.status_code == 200:
                    self.project_created_at = repo_response.json().get('created_at')
            except Exception as e:
                logger.warning(f"Could not fetch repo creation date: {e}")
            
            # Store project_created_at in the data for later use by CSV generator
            all_data['project_created_at'] = self.project_created_at

            # Get collected PR numbers to skip
            collected_prs = set()
            if existing_data:
                collected_prs = {
                    pr["pull_request_number"]
                    for pr in existing_data.get("pull_requests", [])
                }

            # Get total PR count upfront (GraphQL with Link header fallback)
            total_prs = self._get_total_pr_count(filters)
            has_date_filter = filters and (filters.get("start_date") or filters.get("end_date"))
            logger.info(f"Total PR count: {total_prs}")

            # Immediately report total so the frontend can display it during pagination
            if progress_callback and total_prs > 0:
                progress_callback(
                    len(collected_prs), total_prs, "Starting collection..."
                )

            # Process PRs page by page — no full pre-scan needed
            collected_count = len(collected_prs)
            failed_prs = []
            page = 1

            while True:
                logger.info(f"Fetching page {page}")
                prs = self._get_pull_requests_page(page, filters)

                if not prs:
                    logger.info(f"No more PRs found on page {page}")
                    break

                logger.info(f"Found {len(prs)} PRs on page {page}")

                for pr in prs:
                    # Skip already collected PRs (resume support)
                    if pr['number'] in collected_prs:
                        continue

                    # Apply date filter (GitHub API doesn't support date filtering on pulls endpoint)
                    if has_date_filter:
                        pr_created = pr.get('created_at', '')
                        if pr_created:
                            pr_date = datetime.fromisoformat(pr_created.replace('Z', '+00:00')).date()
                            if filters.get("start_date") and pr_date < filters["start_date"]:
                                continue
                            if filters.get("end_date") and pr_date > filters["end_date"]:
                                continue

                    try:
                        pr_data = self._process_pull_request(pr['number'])
                    except Exception as e:
                        logger.warning(f"Skipping PR #{pr['number']} due to error: {e}")
                        failed_prs.append(pr['number'])
                        continue

                    if pr_data:
                        all_data["pull_requests"].append(pr_data)
                        collected_count += 1

                        # Update progress with item data for incremental saving
                        if progress_callback:
                            progress_callback(
                                collected_count,
                                total_prs,
                                f"Collected PR #{pr['number']}",
                                pr_data,
                                all_data
                            )

                page += 1
            
            if failed_prs:
                logger.warning(f"Failed to collect {len(failed_prs)} PRs: {failed_prs}")

            # Update total_prs to actual count now that we've seen all pages
            total_prs = collected_count
            if progress_callback:
                progress_callback(
                    collected_count, total_prs, "Finalizing..."
                )
            
            # Deduplicate PRs by pull_request_number as a safety net
            seen = {}
            for pr in all_data['pull_requests']:
                seen[pr['pull_request_number']] = pr
            all_data['pull_requests'] = list(seen.values())
            
            logger.info(f"Collection completed: {len(all_data['pull_requests'])} unique PRs")
            
            return all_data

        except Exception as e:
            logger.error(f"Error collecting data: {e}")
            raise

    def _get_total_pr_count(self, filters=None):
        """
        Get total PR count using GitHub GraphQL API for exact results.
        Falls back to Link header method if GraphQL fails.
        """
        try:
            return self._get_total_pr_count_graphql(filters)
        except Exception as e:
            logger.warning(f"GraphQL total count failed, falling back to Link header: {e}")
            return self._get_total_pr_count_link_header(filters)

    def _get_total_pr_count_graphql(self, filters=None):
        """Get exact PR count using GitHub GraphQL API."""
        graphql_url = "https://api.github.com/graphql"
        graphql_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        has_date_filter = filters and (filters.get("start_date") or filters.get("end_date"))

        if has_date_filter:
            # Use search query for date-filtered counts
            query_parts = [f"repo:{self.repo_full_name}", "is:pr"]

            if self.branch_name:
                query_parts.append(f"base:{self.branch_name}")

            start = filters.get("start_date") if filters else None
            end = filters.get("end_date") if filters else None
            if start and end:
                s = start.isoformat() if hasattr(start, 'isoformat') else start
                e = end.isoformat() if hasattr(end, 'isoformat') else end
                query_parts.append(f"created:{s}..{e}")
            elif start:
                s = start.isoformat() if hasattr(start, 'isoformat') else start
                query_parts.append(f"created:>={s}")
            elif end:
                e = end.isoformat() if hasattr(end, 'isoformat') else end
                query_parts.append(f"created:<={e}")

            graphql_query = """
            query($searchQuery: String!) {
                search(query: $searchQuery, type: ISSUE) {
                    issueCount
                }
            }
            """
            variables = {"searchQuery": " ".join(query_parts)}

            response = self.session.post(
                graphql_url,
                json={"query": graphql_query, "variables": variables},
                headers=graphql_headers,
                timeout=30,
            )
            if response.status_code != 200:
                raise Exception(f"GitHub GraphQL HTTP {response.status_code}")

            data = response.json()
            if "errors" in data:
                raise Exception(f"GraphQL errors: {data['errors']}")

            return data["data"]["search"]["issueCount"]
        else:
            # No date filter - use repository.pullRequests.totalCount (exact)
            owner, name = self.repo_full_name.split("/", 1)
            graphql_query = """
            query($owner: String!, $name: String!, $baseRefName: String) {
                repository(owner: $owner, name: $name) {
                    pullRequests(baseRefName: $baseRefName) {
                        totalCount
                    }
                }
            }
            """
            variables = {"owner": owner, "name": name}
            if self.branch_name:
                variables["baseRefName"] = self.branch_name

            response = self.session.post(
                graphql_url,
                json={"query": graphql_query, "variables": variables},
                headers=graphql_headers,
                timeout=30,
            )
            if response.status_code != 200:
                raise Exception(f"GitHub GraphQL HTTP {response.status_code}")

            data = response.json()
            if "errors" in data:
                raise Exception(f"GraphQL errors: {data['errors']}")

            return data["data"]["repository"]["pullRequests"]["totalCount"]

    def _get_total_pr_count_link_header(self, filters=None):
        """Fallback: get total PR count using Link header pagination trick."""
        try:
            params = {
                'state': 'all',
                'per_page': 1,
                'page': 1,
            }
            if self.branch_name:
                params['base'] = self.branch_name

            response = self.session.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls",
                params=params,
                timeout=30,
            )
            if response.status_code == 200:
                link_header = response.headers.get('Link', '')
                if link_header:
                    match = re.search(r'page=(\d+)>;\s*rel="last"', link_header)
                    if match:
                        return int(match.group(1))
                data = response.json()
                return len(data)
            return 0
        except Exception as e:
            logger.warning(f"Could not get total PR count via Link header: {e}")
            return 0

    def _get_pull_requests_page(self, page, filters=None):
        """Get one page of pull requests"""
        try:
            params = {
                'state': 'all',
                'per_page': 100,
                'page': page,
                'sort': 'created',
                'direction': 'desc',
            }

            # Apply branch filter
            if self.branch_name:
                params['base'] = self.branch_name
            
            response = self.session.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls",
                params=params,
                timeout=30,
            )

            if response.status_code == 401:
                raise Exception(
                    "GitHub token invalid or expired. Please update the token in workspace settings."
                )

            if response.status_code == 404:
                raise Exception(f"Repository not found: {self.repo_full_name}")

            if response.status_code != 200:
                raise Exception(f"GitHub API error: {response.status_code}")

            return response.json()

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Network connection error: {e}")
            raise Exception(f"Network connection lost while fetching PRs: {str(e)}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise Exception(f"Request timeout while fetching PRs: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching PR page: {e}")
            raise Exception(f"Network error connecting to GitHub: {str(e)}")
    
    def _needs_endpoint(self, endpoint_key):
        """Check if a given endpoint category is needed based on selected metrics."""
        if self.required_endpoints is None:
            return True
        return endpoint_key in self.required_endpoints

    def _process_pull_request(self, pr_number):
        """Process a single pull request - raises exception on network errors"""
        try:
            pr_response = self.session.get(
                f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}",
                timeout=30
            )

            if pr_response.status_code == 401:
                raise Exception("GitHub token invalid or expired.")

            if pr_response.status_code != 200:
                logger.warning(
                    f"Failed to fetch PR #{pr_number}: {pr_response.status_code}"
                )
                raise Exception(
                    f"Failed to fetch PR #{pr_number}: HTTP {pr_response.status_code}"
                )

            pr_details = pr_response.json()

            organized_pr = {
                "pull_request_number": pr_number,
                "details": pr_details,
                "commits": [],
                "comments": [],
                "reviews": [],
                "review_comments": [],
                "files": [],
                "commit_comments": [],
            }

            # Get commits (only if selected)
            if self._needs_endpoint('commits'):
                try:
                    commits_response = self.session.get(
                        f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/commits",
                        params={'per_page': 100},
                        timeout=30
                    )

                    if commits_response.status_code == 200:
                        commits = commits_response.json()
                        for commit in commits:
                            commit_detail = self._get_commit_details(commit['sha'])
                            organized_pr['commits'].append({
                                'commit_sha': commit['sha'],
                                'details': commit,
                                'changes': commit_detail.get('files', []) if commit_detail else []
                            })
                            # Commit-level comments (rare; qualitative enrichment only)
                            if self.for_qualitative:
                                cc = self._collect_commit_comments(commit['sha'])
                                if cc:
                                    organized_pr['commit_comments'].extend(cc)
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error fetching commits for PR #{pr_number}: {e}")
                    raise Exception(f"Network error fetching commits for PR #{pr_number}: {str(e)}")
            
            # Get comments (only if selected)
            if self._needs_endpoint('comments'):
                try:
                    comments_response = self.session.get(
                        f"{self.base_url}/repos/{self.repo_full_name}/issues/{pr_number}/comments",
                        timeout=30
                    )
                    
                    if comments_response.status_code == 200:
                        organized_pr['comments'] = comments_response.json()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error fetching comments for PR #{pr_number}: {e}")
                    raise Exception(f"Network error fetching comments for PR #{pr_number}: {str(e)}")
            
            # Get reviews (only if selected)
            if self._needs_endpoint('reviews'):
                try:
                    reviews_response = self.session.get(
                        f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/reviews",
                        timeout=30
                    )
                    
                    if reviews_response.status_code == 200:
                        organized_pr['reviews'] = reviews_response.json()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error fetching reviews for PR #{pr_number}: {e}")
                    raise Exception(f"Network error fetching reviews for PR #{pr_number}: {str(e)}")
            
            # Get review comments (only if selected)
            if self._needs_endpoint('review_comments'):
                try:
                    review_comments_response = self.session.get(
                        f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/comments",
                        timeout=30
                    )
                    
                    if review_comments_response.status_code == 200:
                        organized_pr['review_comments'] = review_comments_response.json()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error fetching review comments for PR #{pr_number}: {e}")
                    raise Exception(f"Network error fetching review comments for PR #{pr_number}: {str(e)}")
            
            # Get files changed (only if selected)
            if self._needs_endpoint('files'):
                try:
                    files_response = self.session.get(
                        f"{self.base_url}/repos/{self.repo_full_name}/pulls/{pr_number}/files",
                        timeout=30
                    )
                    
                    if files_response.status_code == 200:
                        organized_pr['files'] = files_response.json()
                except requests.exceptions.RequestException as e:
                    logger.error(f"Network error fetching files for PR #{pr_number}: {e}")
                    raise Exception(f"Network error fetching files for PR #{pr_number}: {str(e)}")

            # Qualitative enrichment: review-thread resolution/threading (GraphQL) and
            # reactions on general comments. Added under new keys so existing consumers
            # (CSV generation, cleaning, metrics) are unaffected.
            if self.for_qualitative:
                organized_pr['review_threads'] = self._collect_review_threads(pr_number)
                for comment in organized_pr.get('comments', []):
                    comment_id = comment.get('id')
                    if comment_id is not None:
                        comment['reactions'] = self._collect_issue_comment_reactions(comment_id)

            return organized_pr

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Network connection lost processing PR #{pr_number}: {e}")
            raise Exception(f"Network connection lost while processing PR #{pr_number}")
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout processing PR #{pr_number}: {e}")
            raise Exception(f"Request timeout while processing PR #{pr_number}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error processing PR {pr_number}: {e}")
            raise Exception(f"Network error processing PR #{pr_number}: {str(e)}")

    def _get_commit_details(self, commit_sha):
        """Get commit details with file changes"""
        try:
            response = self.session.get(
                f"{self.base_url}/repos/{self.repo_full_name}/commits/{commit_sha}",
                timeout=30
            )

            if response.status_code == 200:
                return response.json()

            return None

        except Exception as e:
            logger.warning(f"Error getting commit details for {commit_sha}: {e}")
            return None

    def _collect_commit_comments(self, commit_sha):
        """Fetch comments left directly on a commit (qualitative enrichment).

        These are the rare 'commit comment' review type, made outside the PR
        review threads. Returns the raw comment objects (each already carries
        commit_id). Never raises — best-effort.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/repos/{self.repo_full_name}/commits/{commit_sha}/comments",
                params={'per_page': 100},
                timeout=30,
            )
            if response.status_code != 200:
                return []
            return response.json()
        except Exception as e:
            logger.warning(f"Error fetching commit comments for {commit_sha}: {e}")
            return []

    def _collect_issue_comment_reactions(self, comment_id):
        """Fetch reactions on a general/issue comment (qualitative enrichment).

        Returns a normalized list of {"content", "user"} dicts. Never raises:
        reactions are a best-effort signal and must not abort a collection.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/repos/{self.repo_full_name}/issues/comments/{comment_id}/reactions",
                params={'per_page': 100},
                timeout=30,
            )
            if response.status_code != 200:
                return []
            return [
                {"content": r.get("content"), "user": (r.get("user") or {}).get("login")}
                for r in response.json()
            ]
        except Exception as e:
            logger.warning(f"Error fetching reactions for comment {comment_id}: {e}")
            return []

    def _collect_review_threads(self, pr_number):
        """Collect inline review threads via GraphQL (qualitative enrichment).

        Provides isResolved / isOutdated, reply/thread structure and inline-comment
        reactions — none of which the REST pulls/{n}/comments endpoint returns.
        Returns a list of normalized thread dicts. Never raises: on any failure it
        returns whatever was collected so far (possibly empty).
        """
        graphql_url = "https://api.github.com/graphql"
        graphql_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        # Page sizes are kept small because GitHub rejects a query whose nested
        # connections multiply past 500,000 possible nodes (MAX_NODE_LIMIT_EXCEEDED).
        # 20 x 50 x 10 = ~11k nodes. reviewThreads is paginated via endCursor below.
        query = """
        query($owner: String!, $name: String!, $number: Int!, $after: String) {
          repository(owner: $owner, name: $name) {
            pullRequest(number: $number) {
              reviewThreads(first: 20, after: $after) {
                pageInfo { hasNextPage endCursor }
                nodes {
                  id
                  isResolved
                  isOutdated
                  path
                  line
                  originalLine
                  diffSide
                  comments(first: 50) {
                    nodes {
                      databaseId
                      body
                      diffHunk
                      path
                      line
                      originalLine
                      createdAt
                      updatedAt
                      author { __typename login }
                      replyTo { databaseId }
                      pullRequestReview { databaseId }
                      reactions(first: 10) { nodes { content user { login } } }
                    }
                  }
                }
              }
            }
          }
        }
        """
        try:
            owner, name = self.repo_full_name.split("/", 1)
        except ValueError:
            return []

        threads = []
        after = None
        try:
            while True:
                variables = {"owner": owner, "name": name, "number": int(pr_number), "after": after}
                response = self.session.post(
                    graphql_url,
                    json={"query": query, "variables": variables},
                    headers=graphql_headers,
                    timeout=30,
                )
                if response.status_code != 200:
                    logger.warning(
                        f"reviewThreads GraphQL HTTP {response.status_code} for PR #{pr_number}"
                    )
                    break

                data = response.json()
                if data.get("errors"):
                    logger.warning(
                        f"reviewThreads GraphQL errors for PR #{pr_number}: {data['errors']}"
                    )
                    break

                pr_node = (
                    data.get("data", {}).get("repository", {}) or {}
                ).get("pullRequest")
                if not pr_node:
                    break

                rt = pr_node.get("reviewThreads", {}) or {}
                for node in rt.get("nodes", []) or []:
                    threads.append(self._normalize_review_thread(node))

                page_info = rt.get("pageInfo", {}) or {}
                if page_info.get("hasNextPage"):
                    after = page_info.get("endCursor")
                else:
                    break
        except Exception as e:
            logger.warning(f"Error collecting review threads for PR #{pr_number}: {e}")

        return threads

    @staticmethod
    def _normalize_review_thread(node):
        """Shape a GraphQL reviewThread node into a stable, ETL-friendly dict."""
        side = node.get("diffSide")
        comments = []
        for c in (node.get("comments", {}) or {}).get("nodes", []) or []:
            author = c.get("author") or {}
            reactions = [
                {"content": r.get("content"), "user": (r.get("user") or {}).get("login")}
                for r in (c.get("reactions", {}) or {}).get("nodes", []) or []
            ]
            comments.append({
                "id": c.get("databaseId"),
                "body": c.get("body"),
                "diff_hunk": c.get("diffHunk"),
                "path": c.get("path"),
                "line": c.get("line"),
                "original_line": c.get("originalLine"),
                "side": side,
                "created_at": c.get("createdAt"),
                "updated_at": c.get("updatedAt"),
                "author": author.get("login"),
                "author_is_bot": author.get("__typename") == "Bot",
                "reply_to_id": (c.get("replyTo") or {}).get("databaseId"),
                "review_id": (c.get("pullRequestReview") or {}).get("databaseId"),
                "reactions": reactions,
            })
        return {
            "id": node.get("id"),
            "is_resolved": node.get("isResolved"),
            "is_outdated": node.get("isOutdated"),
            "path": node.get("path"),
            "line": node.get("line"),
            "original_line": node.get("originalLine"),
            "side": side,
            "comments": comments,
        }
