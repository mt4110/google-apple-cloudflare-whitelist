"""Public IP range fetcher and network allowlist generator."""

__version__ = "0.4.0"

from .core import (
    CLOUDFLARE_IPS_V4_URL,
    CLOUDFLARE_IPS_V6_URL,
    DEFAULT_APPLE_IPV4,
    DEFAULT_APPLE_IPV6,
    GOOGLE_CLOUD_JSON,
    GOOGLE_GOOG_JSON,
)
from .matching import (
    has_apple_whitelist_cidr,
    has_exact_cidr,
    is_apple_whitelist_ip,
    is_ip_in_networks,
    load_apple_whitelist_networks,
    load_networks,
    load_networks_from_paths,
    resolve_effective_client_ip,
)

__all__ = [
    "CLOUDFLARE_IPS_V4_URL",
    "CLOUDFLARE_IPS_V6_URL",
    "DEFAULT_APPLE_IPV4",
    "DEFAULT_APPLE_IPV6",
    "GOOGLE_CLOUD_JSON",
    "GOOGLE_GOOG_JSON",
    "has_apple_whitelist_cidr",
    "has_exact_cidr",
    "is_apple_whitelist_ip",
    "is_ip_in_networks",
    "load_apple_whitelist_networks",
    "load_networks",
    "load_networks_from_paths",
    "resolve_effective_client_ip",
]
