from __future__ import annotations

"""Helpers for IP / CIDR matching against generated allowlist files.

These helpers intentionally distinguish between two different questions:

1. "Is this concrete IP inside the Apple allowlist?"
2. "Does this exact CIDR exist in the Apple allowlist?"

Those are related, but not the same. For example, ``17.1.2.3`` is an IP address
that belongs to ``17.0.0.0/8``, while ``17.0.0.0/8`` itself is the CIDR entry.
"""

import ipaddress
import pathlib
from typing import Iterable

from .core import AppleRanges

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network
IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
PathLike = pathlib.Path | str


def _to_path(path: PathLike) -> pathlib.Path:
    return path if isinstance(path, pathlib.Path) else pathlib.Path(path)


def load_networks(path: PathLike) -> tuple[IPNetwork, ...]:
    """Load CIDRs from a txt file where each line is a single CIDR."""
    resolved = _to_path(path)
    lines = [line.strip() for line in resolved.read_text(encoding="utf-8").splitlines() if line.strip()]
    return tuple(ipaddress.ip_network(line) for line in lines)


def load_networks_from_paths(*paths: PathLike) -> tuple[IPNetwork, ...]:
    """Load and concatenate CIDRs from multiple txt files."""
    networks: list[IPNetwork] = []
    for path in paths:
        networks.extend(load_networks(path))
    return tuple(networks)


def load_apple_whitelist_networks(
    *,
    output_dir: PathLike | None = None,
    ipv4_path: PathLike | None = None,
    ipv6_path: PathLike | None = None,
) -> tuple[IPNetwork, ...]:
    """Load Apple allowlist CIDRs.

    Precedence:
    1. ``output_dir`` -> read ``apple_owned_ipv4.txt`` and ``apple_owned_ipv6.txt``.
    2. Explicit ``ipv4_path`` / ``ipv6_path`` txt files.
    3. Bundled default Apple coarse ranges from package data.
    """
    if output_dir is not None:
        root = _to_path(output_dir)
        return load_networks_from_paths(root / "apple_owned_ipv4.txt", root / "apple_owned_ipv6.txt")

    explicit_paths: list[pathlib.Path] = []
    if ipv4_path is not None:
        explicit_paths.append(_to_path(ipv4_path))
    if ipv6_path is not None:
        explicit_paths.append(_to_path(ipv6_path))
    if explicit_paths:
        return load_networks_from_paths(*explicit_paths)

    bundled = AppleRanges.default()
    return tuple(ipaddress.ip_network(cidr) for cidr in (*bundled.ipv4, *bundled.ipv6))


def parse_ip(candidate_ip: str) -> IPAddress:
    return ipaddress.ip_address(candidate_ip)


def parse_network(candidate_cidr: str) -> IPNetwork:
    return ipaddress.ip_network(candidate_cidr)


def is_ip_in_networks(candidate_ip: str, networks: Iterable[IPNetwork]) -> bool:
    """Return True when the concrete IP belongs to at least one CIDR."""
    ip = parse_ip(candidate_ip)
    return any(ip in network for network in networks)


def has_exact_cidr(candidate_cidr: str, networks: Iterable[IPNetwork]) -> bool:
    """Return True when the exact CIDR exists in the allowlist.

    This is *not* a containment check. ``17.0.0.0/16`` does not match just
    because ``17.0.0.0/8`` exists.
    """
    candidate_network = parse_network(candidate_cidr)
    return any(candidate_network == network for network in networks)


def is_apple_whitelist_ip(
    candidate_ip: str,
    *,
    output_dir: PathLike | None = None,
    ipv4_path: PathLike | None = None,
    ipv6_path: PathLike | None = None,
    networks: Iterable[IPNetwork] | None = None,
) -> bool:
    """Return True when the IP belongs to the Apple allowlist."""
    selected_networks = tuple(networks) if networks is not None else load_apple_whitelist_networks(
        output_dir=output_dir,
        ipv4_path=ipv4_path,
        ipv6_path=ipv6_path,
    )
    return is_ip_in_networks(candidate_ip, selected_networks)


def has_apple_whitelist_cidr(
    candidate_cidr: str,
    *,
    output_dir: PathLike | None = None,
    ipv4_path: PathLike | None = None,
    ipv6_path: PathLike | None = None,
    networks: Iterable[IPNetwork] | None = None,
) -> bool:
    """Return True when the exact CIDR exists in the Apple allowlist."""
    selected_networks = tuple(networks) if networks is not None else load_apple_whitelist_networks(
        output_dir=output_dir,
        ipv4_path=ipv4_path,
        ipv6_path=ipv6_path,
    )
    return has_exact_cidr(candidate_cidr, selected_networks)


def resolve_effective_client_ip(
    remote_addr: str,
    forwarded_ip: str | None,
    trusted_proxy_networks: Iterable[IPNetwork],
) -> str:
    """Trust a forwarded client IP only when the direct peer is trusted.

    Example: trust ``CF-Connecting-IP`` only when ``remote_addr`` belongs to the
    Cloudflare proxy ranges that you allow to reach your origin.
    """
    if forwarded_ip and is_ip_in_networks(remote_addr, trusted_proxy_networks):
        try:
            return str(parse_ip(forwarded_ip.strip()))
        except ValueError:
            return remote_addr
    return remote_addr
