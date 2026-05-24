"""
source_utils.py — NewsSource resolution utilities.

When a news article is predicted, the Chrome extension extracts the domain
from the page URL and sends it to the backend. This module handles:

  1. Looking up an existing NewsSource by domain.
  2. If not found, generating a logo URL using the Google Favicon Service
     (free, no API key, no rate limits) and formatting the domain as a
     readable name.
  3. Creating the new NewsSource and returning it.

Google Favicon Service:
  URL: https://www.google.com/s2/favicons?domain=<domain>&sz=128
  - Completely free, no authentication required
  - Returns the favicon of any website at the requested size
  - sz parameter: 16, 32, 64 or 128 (pixels)
"""

from .models import NewsSource

GOOGLE_FAVICON_URL = "https://www.google.com/s2/favicons?domain={domain}&sz=128"


def _get_favicon_url(domain: str) -> str:
    """
    Returns the Google Favicon Service URL for a given domain.
    Always works — Google returns a default icon if the domain has no favicon.
    """
    return GOOGLE_FAVICON_URL.format(domain=domain)


def get_or_create_source(domain: str) -> NewsSource:
    """
    Main entry point: given a domain string, returns the matching
    NewsSource, creating it if it does not exist yet.

    For unknown domains, the name is derived from the domain itself
    and the logo is set to the Google Favicon Service URL, which
    automatically resolves the website's favicon with no API calls needed.

    Args:
        domain: lowercase domain string, e.g. "bbc.com", "timesofisrael.com"

    Returns:
        NewsSource instance (existing or newly created)
    """
    domain = domain.lower().strip()

    try:
        return NewsSource.objects.get(domain=domain)
    except NewsSource.DoesNotExist:
        pass

    source, _ = NewsSource.objects.get_or_create(
        domain=domain,
        defaults={
            "name": None,  # ← unknown, frontend shows domain instead
            "logo_url": _get_favicon_url(domain),
            "is_predefined": False,
        },
    )
    return source
