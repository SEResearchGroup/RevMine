import requests
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class GitLabCollector:
    """Collects data from GitLab API with resume capability"""

    def __init__(
        self,
        token,
        repo_full_name,
        base_url="https://gitlab.com/api/v4",
        branch_name=None,
        project_id=None,
    ):
        self.token = token
        self.repo_full_name = repo_full_name
        self.branch_name = branch_name
        self.base_url = base_url
        self.headers = {"PRIVATE-TOKEN": token}
        self.project_id = project_id  # Can be passed directly from external_id

    def collect_all_data(
        self, filters=None, progress_callback=None, resume_from=None, existing_data=None
    ):
        """
        Collect all merge request data with progress updates and resume support

        Args:
            filters (dict): Date and status filters
            progress_callback (callable): Function to call with progress updates (current, total, message, item_data)
            resume_from (str): MR IID to resume from (if resuming)
            existing_data (dict): Existing collected data (if resuming)

        Returns:
            dict: All collected data organized by type
        """
        if existing_data:
            all_data = existing_data
        else:
            all_data = {"merge_requests": []}

        try:
            # Get project ID if not already set
            if not self.project_id:
                self.project_id = self._get_project_id()

            if not self.project_id:
                raise Exception(
                    "Could not get project ID. Please check the repository configuration."
                )

            logger.info(f"Project ID: {self.project_id}")

            # Get collected MR IIDs to skip
            collected_mrs = set()
            if existing_data:
                collected_mrs = {
                    mr["merge_request_id"]
                    for mr in existing_data.get("merge_requests", [])
                }

            # First pass: Collect all MRs to get accurate count
            logger.info("Collecting MRs...")
            all_mrs = []
            page = 1

            while True:
                logger.info(f"Fetching page {page}")
                mrs = self._get_merge_requests_page(page, filters)

                if not mrs:
                    logger.info(f"No more MRs found on page {page}")
                    break

                logger.info(f"Found {len(mrs)} MRs on page {page}")
                all_mrs.extend(mrs)
                page += 1

                # Safety limit to prevent infinite loops
                if page > 50:
                    logger.warning("Reached page limit (50), stopping pagination")
                    break

            # Filter out already collected MRs
            if resume_from:
                resume_mr_iid = int(resume_from)
                all_mrs = [mr for mr in all_mrs if mr["iid"] not in collected_mrs]

            total_mrs = len(all_mrs) + len(collected_mrs)
            logger.info(
                f"Total MRs to process: {len(all_mrs)} (already collected: {len(collected_mrs)})"
            )

            if progress_callback:
                progress_callback(
                    len(collected_mrs), total_mrs, "Starting collection..."
                )

            # Process each MR
            collected_count = len(collected_mrs)

            for mr in all_mrs:
                mr_data = self._process_merge_request(mr["iid"])
                if mr_data:
                    all_data["merge_requests"].append(mr_data)
                    collected_count += 1

                    # Update progress with item data for incremental saving
                    if progress_callback:
                        progress_callback(
                            collected_count,
                            total_mrs,
                            f"Collected MR !{mr['iid']}",
                            mr_data,
                        )

            logger.info(f"Collection completed: {collected_count} MRs")

            return all_data

        except Exception as e:
            logger.error(f"Error collecting data: {e}")
            raise

    def _get_project_id(self):
        """Get GitLab project ID from full name"""
        try:
            encoded_path = self.repo_full_name.replace("/", "%2F")
            response = requests.get(
                f"{self.base_url}/projects/{encoded_path}",
                headers=self.headers,
                verify=False,
                timeout=30,
            )

            if response.status_code == 200:
                return str(response.json()["id"])

            return None

        except Exception as e:
            logger.error(f"Error getting project ID: {e}")
            return None

    def _get_merge_requests_page(self, page, filters=None):
        """Get one page of merge requests"""
        try:
            params = {
                "page": page,
                "per_page": 100,  # Increased for efficiency
                "state": "all",  # Get all MRs (opened, closed, merged)
            }

            # Apply status filter if provided
            if filters and filters.get("status"):
                status_list = filters["status"]
                # GitLab uses 'opened', 'closed', 'merged', 'all'
                # Map frontend values to GitLab values
                gitlab_states = []
                for s in status_list:
                    if s == "open":
                        gitlab_states.append("opened")
                    elif s in ["closed", "merged"]:
                        gitlab_states.append(s)

                # If all states selected or status list has all options, use 'all'
                if len(gitlab_states) >= 3 or set(gitlab_states) == {
                    "opened",
                    "closed",
                    "merged",
                }:
                    params["state"] = "all"
                elif len(gitlab_states) == 1:
                    params["state"] = gitlab_states[0]
                # GitLab doesn't support multiple states, so we use 'all' and filter later if needed

            # Apply date filters if provided
            if filters:
                if filters.get("start_date"):
                    params["created_after"] = (
                        filters["start_date"].isoformat()
                        if hasattr(filters["start_date"], "isoformat")
                        else filters["start_date"]
                    )
                if filters.get("end_date"):
                    params["created_before"] = (
                        filters["end_date"].isoformat()
                        if hasattr(filters["end_date"], "isoformat")
                        else filters["end_date"]
                    )

            # Apply branch filter (target_branch)
            if self.branch_name:
                params["target_branch"] = self.branch_name

            logger.info(f"Fetching MRs with params: {params}")

            response = requests.get(
                f"{self.base_url}/projects/{self.project_id}/merge_requests",
                headers=self.headers,
                params=params,
                verify=False,
                timeout=30,
            )

            if response.status_code == 401:
                error_msg = "Token GitLab invalide ou expiré. Veuillez mettre à jour le token dans les paramètres du workspace."
                try:
                    error_data = response.json()
                    if error_data.get("error_description"):
                        error_msg = f"Erreur d'authentification GitLab: {error_data['error_description']}"
                except:
                    pass
                logger.error(f"Authentication error: {error_msg}")
                raise Exception(error_msg)

            if response.status_code == 404:
                logger.error(f"Project not found: {self.project_id}")
                raise Exception(
                    f"Projet GitLab non trouvé (ID: {self.project_id}). Vérifiez que le projet existe et que vous avez les permissions."
                )

            if response.status_code != 200:
                logger.error(
                    f"Error fetching MRs: {response.status_code} - {response.text}"
                )
                raise Exception(f"Erreur GitLab API: {response.status_code}")

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching MR page: {e}")
            raise Exception(f"Erreur réseau lors de la connexion à GitLab: {str(e)}")

    def _process_merge_request(self, mr_iid):
        """Process a single merge request - raises exception on network errors"""
        try:
            mr_response = requests.get(
                f"{self.base_url}/projects/{self.project_id}/merge_requests/{mr_iid}",
                headers=self.headers,
                verify=False,
                timeout=30,
            )

            if mr_response.status_code == 401:
                raise Exception("Token GitLab invalide ou expiré.")

            if mr_response.status_code != 200:
                logger.warning(
                    f"Failed to fetch MR !{mr_iid}: {mr_response.status_code}"
                )
                raise Exception(
                    f"Échec de la récupération de MR !{mr_iid}: HTTP {mr_response.status_code}"
                )

            mr_details = mr_response.json()

            organized_mr = {
                "merge_request_id": mr_iid,
                "details": mr_details,
                "commits": [],
                "discussions": [],
                "notes": [],
                "changes": [],
            }

            # Get commits
            try:
                commits_response = requests.get(
                    f"{self.base_url}/projects/{self.project_id}/merge_requests/{mr_iid}/commits",
                    headers=self.headers,
                    params={"per_page": 9999},
                    verify=False,
                    timeout=30,
                )

                if commits_response.status_code == 200:
                    commits = commits_response.json()
                    for commit in commits:
                        commit_diff = self._get_commit_diff(commit["short_id"])
                        organized_mr["commits"].append(
                            {
                                "commit_id": commit["short_id"],
                                "details": commit,
                                "changesHist": commit_diff,
                            }
                        )
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error fetching commits for MR !{mr_iid}: {e}")
                raise Exception(
                    f"Erreur réseau lors de la récupération des commits pour MR !{mr_iid}: {str(e)}"
                )

            # Get discussions
            try:
                discussions_response = requests.get(
                    f"{self.base_url}/projects/{self.project_id}/merge_requests/{mr_iid}/discussions",
                    headers=self.headers,
                    verify=False,
                    timeout=30,
                )

                if discussions_response.status_code == 200:
                    organized_mr["discussions"] = discussions_response.json()
            except requests.exceptions.RequestException as e:
                logger.error(
                    f"Network error fetching discussions for MR !{mr_iid}: {e}"
                )
                raise Exception(
                    f"Erreur réseau lors de la récupération des discussions pour MR !{mr_iid}: {str(e)}"
                )

            # Get notes
            try:
                notes_response = requests.get(
                    f"{self.base_url}/projects/{self.project_id}/merge_requests/{mr_iid}/notes",
                    headers=self.headers,
                    verify=False,
                    timeout=30,
                )

                if notes_response.status_code == 200:
                    organized_mr["notes"] = notes_response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error fetching notes for MR !{mr_iid}: {e}")
                raise Exception(
                    f"Erreur réseau lors de la récupération des notes pour MR !{mr_iid}: {str(e)}"
                )

            # Get changes
            try:
                changes_response = requests.get(
                    f"{self.base_url}/projects/{self.project_id}/merge_requests/{mr_iid}/changes",
                    headers=self.headers,
                    verify=False,
                    timeout=30,
                )

                if changes_response.status_code == 200:
                    organized_mr["changes"] = changes_response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error fetching changes for MR !{mr_iid}: {e}")
                raise Exception(
                    f"Erreur réseau lors de la récupération des changements pour MR !{mr_iid}: {str(e)}"
                )

            return organized_mr

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Network connection lost processing MR !{mr_iid}: {e}")
            raise Exception(
                f"Connexion réseau perdue lors du traitement de MR !{mr_iid}"
            )
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout processing MR !{mr_iid}: {e}")
            raise Exception(
                f"Délai d'attente dépassé lors du traitement de MR !{mr_iid}"
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error processing MR {mr_iid}: {e}")
            raise Exception(
                f"Erreur réseau lors du traitement de MR !{mr_iid}: {str(e)}"
            )

    def _get_commit_diff(self, commit_id):
        """Get commit diff"""
        try:
            response = requests.get(
                f"{self.base_url}/projects/{self.project_id}/repository/commits/{commit_id}/diff",
                headers=self.headers,
                verify=False,
                timeout=30,
            )

            if response.status_code == 200:
                return response.json()

            return []

        except Exception as e:
            logger.warning(f"Error getting commit diff for {commit_id}: {e}")
            return []
