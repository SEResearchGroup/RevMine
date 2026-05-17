import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def resolve_tls_verify(*ca_bundle_env_names):
    """Return a requests-compatible TLS verification setting.

    Certificate validation stays enabled. Self-hosted GitLab instances with a
    private CA should provide a CA bundle path via one of the environment
    variables, for example ``GITLAB_CA_BUNDLE`` or ``REQUESTS_CA_BUNDLE``.
    """
    for env_name in ca_bundle_env_names or ("REQUESTS_CA_BUNDLE",):
        ca_bundle = os.getenv(env_name)
        if ca_bundle:
            return ca_bundle
    return True


def create_retry_session(
    headers,
    *,
    verify=True,
    max_retries=5,
    backoff_factor=1,
):
    """Create a requests session with retries and TLS verification enabled."""
    session = requests.Session()
    session.headers.update(headers)
    session.verify = verify
    retry = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    for scheme in ("https", "http"):
        session.mount(f"{scheme}://", adapter)
    return session
