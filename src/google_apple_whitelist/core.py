from __future__ import annotations

import ipaddress
import json
import os
import pathlib
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import resources
from typing import Any, Iterable, Mapping, Sequence

from . import __version__

GOOGLE_GOOG_JSON = "https://www.gstatic.com/ipranges/goog.json"
GOOGLE_CLOUD_JSON = "https://www.gstatic.com/ipranges/cloud.json"
CLOUDFLARE_IPS_V4_URL = "https://www.cloudflare.com/ips-v4"
CLOUDFLARE_IPS_V6_URL = "https://www.cloudflare.com/ips-v6"

DEFAULT_APPLE_IPV4 = ("17.0.0.0/8",)
DEFAULT_APPLE_IPV6 = (
    "2403:300::/32",
    "2620:149::/32",
    "2a01:b740::/32",
)

IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network


@dataclass(frozen=True)
class AppleRanges:
    ipv4: tuple[str, ...]
    ipv6: tuple[str, ...]

    @classmethod
    def default(cls) -> "AppleRanges":
        data_path = resources.files("google_apple_whitelist.data").joinpath("apple_ranges.json")
        payload = json.loads(data_path.read_text(encoding="utf-8"))
        return cls.from_mapping(payload)

    @classmethod
    def from_file(cls, path: pathlib.Path) -> "AppleRanges":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_mapping(payload)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "AppleRanges":
        ipv4_raw = payload.get("ipv4", ())
        ipv6_raw = payload.get("ipv6", ())

        if isinstance(ipv4_raw, str):
            ipv4 = (ipv4_raw,)
        elif isinstance(ipv4_raw, Sequence):
            ipv4 = tuple(ipv4_raw)
        else:
            raise ValueError("Apple ranges file field 'ipv4' must be a string or a list of strings.")

        if isinstance(ipv6_raw, str):
            ipv6 = (ipv6_raw,)
        elif isinstance(ipv6_raw, Sequence):
            ipv6 = tuple(ipv6_raw)
        else:
            raise ValueError("Apple ranges file field 'ipv6' must be a string or a list of strings.")

        if any(not isinstance(cidr, str) for cidr in ipv4):
            raise ValueError("Apple ranges file field 'ipv4' must contain only strings.")
        if any(not isinstance(cidr, str) for cidr in ipv6):
            raise ValueError("Apple ranges file field 'ipv6' must contain only strings.")
        if not ipv4 and not ipv6:
            raise ValueError("Apple ranges file must contain at least one IPv4 or IPv6 range.")

        validate_cidrs(ipv4)
        validate_cidrs(ipv6)
        return cls(ipv4=ipv4, ipv6=ipv6)


@dataclass(frozen=True)
class CloudflareRanges:
    ipv4: tuple[str, ...]
    ipv6: tuple[str, ...]

    @classmethod
    def from_text(cls, ipv4_text: str, ipv6_text: str) -> "CloudflareRanges":
        ipv4, _ = collect_text_networks(ipv4_text)
        _, ipv6 = collect_text_networks(ipv6_text)
        return cls(
            ipv4=tuple(str(net) for net in ipv4),
            ipv6=tuple(str(net) for net in ipv6),
        )


@dataclass(frozen=True)
class AllowlistBundle:
    text_files: dict[str, tuple[str, ...]]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class FetchSummary:
    output_dir: pathlib.Path
    goog_creation_time: str | None
    cloud_creation_time: str | None
    cloudflare_retrieved_at: str | None
    counts: dict[str, int]


def validate_cidrs(cidrs: Sequence[str]) -> None:
    for cidr in cidrs:
        ipaddress.ip_network(cidr)


def fetch_json(url: str, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"google-apple-whitelist/{__version__}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return json.loads(response.read().decode(charset))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while fetching {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error while fetching {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {url}: {exc}") from exc


def fetch_text(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"google-apple-whitelist/{__version__}",
            "Accept": "text/plain, text/*;q=0.9, */*;q=0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} while fetching {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error while fetching {url}: {exc.reason}") from exc
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"Invalid text from {url}: {exc}") from exc


def collapse(networks: Iterable[IPNetwork]) -> list[IPNetwork]:
    return list(
        ipaddress.collapse_addresses(
            sorted(networks, key=lambda net: (net.version, int(net.network_address), net.prefixlen))
        )
    )


def collect_networks(feed: Mapping[str, Any]) -> tuple[list[IPNetwork], list[IPNetwork]]:
    ipv4: list[IPNetwork] = []
    ipv6: list[IPNetwork] = []

    for entry in feed.get("prefixes", []):
        v4 = entry.get("ipv4Prefix")
        v6 = entry.get("ipv6Prefix")
        if v4:
            ipv4.append(ipaddress.ip_network(v4))
        if v6:
            ipv6.append(ipaddress.ip_network(v6))

    return collapse(ipv4), collapse(ipv6)


def collect_text_networks(text: str) -> tuple[list[IPNetwork], list[IPNetwork]]:
    ipv4: list[IPNetwork] = []
    ipv6: list[IPNetwork] = []
    for token in text.split():
        network = ipaddress.ip_network(token)
        if network.version == 4:
            ipv4.append(network)
        else:
            ipv6.append(network)
    return collapse(ipv4), collapse(ipv6)


def subtract_networks(base: Sequence[IPNetwork], remove: Sequence[IPNetwork]) -> list[IPNetwork]:
    result: list[IPNetwork] = []
    remove_sorted = sorted(remove, key=lambda net: (net.version, int(net.network_address), net.prefixlen))

    for base_net in base:
        remaining: list[IPNetwork] = [base_net]
        for remove_net in remove_sorted:
            next_remaining: list[IPNetwork] = []
            for current in remaining:
                if current.version != remove_net.version or not current.overlaps(remove_net):
                    next_remaining.append(current)
                    continue
                if remove_net == current or remove_net.supernet_of(current):
                    continue
                if current.supernet_of(remove_net):
                    next_remaining.extend(current.address_exclude(remove_net))
                    continue
                raise RuntimeError(
                    f"Unexpected partial overlap between {current} and {remove_net}."
                )
            remaining = next_remaining
            if not remaining:
                break
        result.extend(remaining)

    return collapse(result)


def _networks_to_strings(networks: Sequence[IPNetwork]) -> tuple[str, ...]:
    return tuple(str(net) for net in networks)


def build_allowlists(
    goog_feed: Mapping[str, Any],
    cloud_feed: Mapping[str, Any],
    apple_ranges: AppleRanges,
    cloudflare_ranges: CloudflareRanges | None = None,
) -> AllowlistBundle:
    goog_v4, goog_v6 = collect_networks(goog_feed)
    cloud_v4, cloud_v6 = collect_networks(cloud_feed)

    google_services_v4 = subtract_networks(goog_v4, cloud_v4)
    google_services_v6 = subtract_networks(goog_v6, cloud_v6)

    apple_v4 = [ipaddress.ip_network(cidr) for cidr in apple_ranges.ipv4]
    apple_v6 = [ipaddress.ip_network(cidr) for cidr in apple_ranges.ipv6]

    combined_owned_v4 = collapse([*goog_v4, *apple_v4])
    combined_owned_v6 = collapse([*goog_v6, *apple_v6])
    combined_services_v4 = collapse([*google_services_v4, *apple_v4])
    combined_services_v6 = collapse([*google_services_v6, *apple_v6])

    cloudflare_v4: list[IPNetwork] = []
    cloudflare_v6: list[IPNetwork] = []
    if cloudflare_ranges is not None:
        cloudflare_v4 = [ipaddress.ip_network(cidr) for cidr in cloudflare_ranges.ipv4]
        cloudflare_v6 = [ipaddress.ip_network(cidr) for cidr in cloudflare_ranges.ipv6]

    combined_owned_with_cloudflare_v4 = collapse([*combined_owned_v4, *cloudflare_v4])
    combined_owned_with_cloudflare_v6 = collapse([*combined_owned_v6, *cloudflare_v6])
    combined_services_with_cloudflare_v4 = collapse([*combined_services_v4, *cloudflare_v4])
    combined_services_with_cloudflare_v6 = collapse([*combined_services_v6, *cloudflare_v6])

    metadata = {
        "sources": {
            "google": {
                "goog_json": GOOGLE_GOOG_JSON,
                "cloud_json": GOOGLE_CLOUD_JSON,
                "goog_creation_time": goog_feed.get("creationTime"),
                "cloud_creation_time": cloud_feed.get("creationTime"),
                "note": "Google publishes goog.json for Google-owned IPs and cloud.json for customer-usable Google Cloud external IP ranges.",
            },
            "apple": {
                "ipv4": list(apple_ranges.ipv4),
                "ipv6": list(apple_ranges.ipv6),
                "note": "Apple publishes coarse IP ranges only. Treat them as maintained allowlist inputs, not as a complete service inventory.",
            },
            "cloudflare": {
                "enabled": cloudflare_ranges is not None,
                "ips_v4_url": CLOUDFLARE_IPS_V4_URL,
                "ips_v6_url": CLOUDFLARE_IPS_V6_URL,
                "note": "Cloudflare IPs let Cloudflare reach your origin. They do not identify the end-user by themselves.",
            },
        },
        "counts": {
            "google_owned_ipv4_prefixes": len(goog_v4),
            "google_owned_ipv6_prefixes": len(goog_v6),
            "google_services_minus_cloud_ipv4_prefixes": len(google_services_v4),
            "google_services_minus_cloud_ipv6_prefixes": len(google_services_v6),
            "apple_owned_ipv4_prefixes": len(apple_v4),
            "apple_owned_ipv6_prefixes": len(apple_v6),
            "cloudflare_proxy_ipv4_prefixes": len(cloudflare_v4),
            "cloudflare_proxy_ipv6_prefixes": len(cloudflare_v6),
        },
        "usage": {
            "strict_origin_ingress": [
                "cloudflare_proxy_ipv4.txt",
                "cloudflare_proxy_ipv6.txt",
            ],
            "egress_google_owned_plus_apple": [
                "combined_google_owned_plus_apple_ipv4.txt",
                "combined_google_owned_plus_apple_ipv6.txt",
            ],
            "egress_google_services_plus_apple": [
                "combined_google_services_plus_apple_ipv4.txt",
                "combined_google_services_plus_apple_ipv6.txt",
            ],
            "statistical_union_only": [
                "combined_google_owned_plus_apple_plus_cloudflare_ipv4.txt",
                "combined_google_owned_plus_apple_plus_cloudflare_ipv6.txt",
                "combined_google_services_plus_apple_plus_cloudflare_ipv4.txt",
                "combined_google_services_plus_apple_plus_cloudflare_ipv6.txt",
            ],
        },
    }

    text_files = {
        "google_owned_ipv4.txt": _networks_to_strings(goog_v4),
        "google_owned_ipv6.txt": _networks_to_strings(goog_v6),
        "google_services_minus_cloud_ipv4.txt": _networks_to_strings(google_services_v4),
        "google_services_minus_cloud_ipv6.txt": _networks_to_strings(google_services_v6),
        "apple_owned_ipv4.txt": _networks_to_strings(apple_v4),
        "apple_owned_ipv6.txt": _networks_to_strings(apple_v6),
        "combined_google_owned_plus_apple_ipv4.txt": _networks_to_strings(combined_owned_v4),
        "combined_google_owned_plus_apple_ipv6.txt": _networks_to_strings(combined_owned_v6),
        "combined_google_services_plus_apple_ipv4.txt": _networks_to_strings(combined_services_v4),
        "combined_google_services_plus_apple_ipv6.txt": _networks_to_strings(combined_services_v6),
        "cloudflare_proxy_ipv4.txt": _networks_to_strings(cloudflare_v4),
        "cloudflare_proxy_ipv6.txt": _networks_to_strings(cloudflare_v6),
        "combined_google_owned_plus_apple_plus_cloudflare_ipv4.txt": _networks_to_strings(combined_owned_with_cloudflare_v4),
        "combined_google_owned_plus_apple_plus_cloudflare_ipv6.txt": _networks_to_strings(combined_owned_with_cloudflare_v6),
        "combined_google_services_plus_apple_plus_cloudflare_ipv4.txt": _networks_to_strings(combined_services_with_cloudflare_v4),
        "combined_google_services_plus_apple_plus_cloudflare_ipv6.txt": _networks_to_strings(combined_services_with_cloudflare_v6),
    }
    return AllowlistBundle(text_files=text_files, metadata=metadata)


def _write_text_atomic(path: pathlib.Path, content: str) -> None:
    fd, tmp_path_str = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = pathlib.Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def write_allowlists(output_dir: pathlib.Path, bundle: AllowlistBundle) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, lines in bundle.text_files.items():
        path = output_dir / filename
        _write_text_atomic(path, "\n".join(lines) + ("\n" if lines else ""))

    metadata_path = output_dir / "metadata.json"
    _write_text_atomic(metadata_path, json.dumps(bundle.metadata, ensure_ascii=False, indent=2) + "\n")


def run_fetch(
    output_dir: pathlib.Path,
    apple_ranges: AppleRanges | None = None,
    include_cloudflare: bool = True,
    timeout: int = 30,
) -> FetchSummary:
    selected_apple_ranges = apple_ranges or AppleRanges.default()
    goog_feed = fetch_json(GOOGLE_GOOG_JSON, timeout=timeout)
    cloud_feed = fetch_json(GOOGLE_CLOUD_JSON, timeout=timeout)
    cloudflare_ranges: CloudflareRanges | None = None
    retrieved_at: str | None = None
    if include_cloudflare:
        cloudflare_ranges = CloudflareRanges.from_text(
            fetch_text(CLOUDFLARE_IPS_V4_URL, timeout=timeout),
            fetch_text(CLOUDFLARE_IPS_V6_URL, timeout=timeout),
        )
        retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    bundle = build_allowlists(
        goog_feed=goog_feed,
        cloud_feed=cloud_feed,
        apple_ranges=selected_apple_ranges,
        cloudflare_ranges=cloudflare_ranges,
    )
    if include_cloudflare:
        bundle.metadata["sources"]["cloudflare"]["retrieved_at"] = retrieved_at
    write_allowlists(output_dir=output_dir, bundle=bundle)
    return FetchSummary(
        output_dir=output_dir,
        goog_creation_time=goog_feed.get("creationTime"),
        cloud_creation_time=cloud_feed.get("creationTime"),
        cloudflare_retrieved_at=retrieved_at,
        counts=bundle.metadata["counts"],
    )
