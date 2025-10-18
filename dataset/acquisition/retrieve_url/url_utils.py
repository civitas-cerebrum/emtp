import urllib.parse
import logging

logger = logging.getLogger(__name__)

def is_denied_domain(url: str, denied_domains: list) -> bool:
    """Checks if a URL belongs to a denied domain."""
    if not denied_domains:
        return False
    try:
        domain = urllib.parse.urlparse(url).netloc
        # Check for direct matches and subdomains
        for denied in denied_domains:
            if domain == denied or domain.endswith(f".{denied}"):
                return True
        return False
    except Exception as e:
        logger.debug(f"Error parsing URL {url} for denied domains check: {e}")
        return False