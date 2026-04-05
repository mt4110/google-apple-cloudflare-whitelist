from __future__ import annotations

import ipaddress
import tempfile
import unittest
from pathlib import Path

from google_apple_whitelist.matching import (
    has_apple_whitelist_cidr,
    has_exact_cidr,
    is_apple_whitelist_ip,
    is_ip_in_networks,
    load_apple_whitelist_networks,
    load_networks,
    load_networks_from_paths,
    resolve_effective_client_ip,
)


class MatchingTests(unittest.TestCase):
    def test_load_networks_reads_txt_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ipv4.txt"
            path.write_text("17.0.0.0/8\n\n", encoding="utf-8")

            loaded = load_networks(path)

        self.assertEqual(tuple(str(net) for net in loaded), ("17.0.0.0/8",))

    def test_load_networks_from_paths_combines_multiple_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ipv4 = Path(tmp) / "ipv4.txt"
            ipv6 = Path(tmp) / "ipv6.txt"
            ipv4.write_text("17.0.0.0/8\n", encoding="utf-8")
            ipv6.write_text("2620:149::/32\n", encoding="utf-8")

            loaded = load_networks_from_paths(ipv4, ipv6)

        self.assertEqual(tuple(str(net) for net in loaded), ("17.0.0.0/8", "2620:149::/32"))

    def test_load_apple_whitelist_networks_uses_bundled_defaults(self) -> None:
        loaded = load_apple_whitelist_networks()
        rendered = tuple(str(net) for net in loaded)

        self.assertIn("17.0.0.0/8", rendered)
        self.assertIn("2620:149::/32", rendered)

    def test_load_apple_whitelist_networks_from_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            (output_dir / "apple_owned_ipv4.txt").write_text("17.0.0.0/8\n", encoding="utf-8")
            (output_dir / "apple_owned_ipv6.txt").write_text("2a01:b740::/32\n", encoding="utf-8")

            loaded = load_apple_whitelist_networks(output_dir=output_dir)

        self.assertEqual(tuple(str(net) for net in loaded), ("17.0.0.0/8", "2a01:b740::/32"))

    def test_is_apple_whitelist_ip_matches_bundled_defaults(self) -> None:
        self.assertTrue(is_apple_whitelist_ip("17.10.20.30"))
        self.assertFalse(is_apple_whitelist_ip("8.8.8.8"))

    def test_has_apple_whitelist_cidr_matches_exact_network_only(self) -> None:
        self.assertTrue(has_apple_whitelist_cidr("17.0.0.0/8"))
        self.assertFalse(has_apple_whitelist_cidr("17.0.0.0/16"))

    def test_generic_helpers_work_for_ip_and_cidr(self) -> None:
        networks = (
            ipaddress.ip_network("17.0.0.0/8"),
            ipaddress.ip_network("2620:149::/32"),
        )

        self.assertTrue(is_ip_in_networks("17.1.2.3", networks))
        self.assertFalse(is_ip_in_networks("8.8.8.8", networks))
        self.assertTrue(has_exact_cidr("17.0.0.0/8", networks))
        self.assertFalse(has_exact_cidr("17.0.0.0/16", networks))

    def test_resolve_effective_client_ip_trusts_forwarded_ip_only_for_trusted_proxy(self) -> None:
        trusted_proxy_networks = (ipaddress.ip_network("173.245.48.0/20"),)

        self.assertEqual(
            resolve_effective_client_ip(
                remote_addr="173.245.48.5",
                forwarded_ip="17.10.20.30",
                trusted_proxy_networks=trusted_proxy_networks,
            ),
            "17.10.20.30",
        )
        self.assertEqual(
            resolve_effective_client_ip(
                remote_addr="198.51.100.20",
                forwarded_ip="17.10.20.30",
                trusted_proxy_networks=trusted_proxy_networks,
            ),
            "198.51.100.20",
        )

    def test_resolve_effective_client_ip_falls_back_when_forwarded_value_is_not_a_single_ip(self) -> None:
        trusted_proxy_networks = (ipaddress.ip_network("173.245.48.0/20"),)

        self.assertEqual(
            resolve_effective_client_ip(
                remote_addr="173.245.48.5",
                forwarded_ip="17.10.20.30, 203.0.113.10",
                trusted_proxy_networks=trusted_proxy_networks,
            ),
            "173.245.48.5",
        )
