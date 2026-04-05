from __future__ import annotations

from pathlib import Path

from google_apple_whitelist.matching import (
    is_apple_whitelist_ip,
    is_ip_in_networks,
    load_networks_from_paths,
    resolve_effective_client_ip,
)


if __name__ == "__main__":
    whitelist_dir = Path("./whitelist_output")

    cloudflare_networks = load_networks_from_paths(
        whitelist_dir / "cloudflare_proxy_ipv4.txt",
        whitelist_dir / "cloudflare_proxy_ipv6.txt",
    )
    provider_networks = load_networks_from_paths(
        whitelist_dir / "combined_google_services_plus_apple_ipv4.txt",
        whitelist_dir / "combined_google_services_plus_apple_ipv6.txt",
    )

    remote_addr = "173.245.48.5"
    cf_connecting_ip = "17.10.20.30"

    effective_ip = resolve_effective_client_ip(
        remote_addr=remote_addr,
        forwarded_ip=cf_connecting_ip,
        trusted_proxy_networks=cloudflare_networks,
    )
    print("effective_ip:", effective_ip)
    print("provider_match:", is_ip_in_networks(effective_ip, provider_networks))
    print(
        "is_apple_whitelist_ip:",
        is_apple_whitelist_ip(effective_ip, output_dir=whitelist_dir),
    )
