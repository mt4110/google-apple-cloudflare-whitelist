from __future__ import annotations

import ipaddress
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from google_apple_whitelist.core import (
    AppleRanges,
    CloudflareRanges,
    build_allowlists,
    collect_networks,
    collect_text_networks,
    run_fetch,
    subtract_networks,
    write_allowlists,
)


class CoreTests(unittest.TestCase):
    def test_collect_networks_separates_ipv4_and_ipv6(self) -> None:
        feed = {
            "prefixes": [
                {"ipv4Prefix": "8.8.8.0/24"},
                {"ipv4Prefix": "8.8.8.0/24"},
                {"ipv6Prefix": "2001:db8::/32"},
            ]
        }

        ipv4, ipv6 = collect_networks(feed)

        self.assertEqual([str(net) for net in ipv4], ["8.8.8.0/24"])
        self.assertEqual([str(net) for net in ipv6], ["2001:db8::/32"])

    def test_collect_text_networks_separates_ipv4_and_ipv6(self) -> None:
        ipv4, ipv6 = collect_text_networks("1.1.1.0/24\n2606:4700::/32\n1.1.1.0/24\n")
        self.assertEqual([str(net) for net in ipv4], ["1.1.1.0/24"])
        self.assertEqual([str(net) for net in ipv6], ["2606:4700::/32"])

    def test_subtract_networks_splits_a_supernet(self) -> None:
        base = [ipaddress.ip_network("10.0.0.0/24")]
        remove = [ipaddress.ip_network("10.0.0.128/25")]

        result = subtract_networks(base, remove)

        self.assertEqual([str(net) for net in result], ["10.0.0.0/25"])

    def test_build_allowlists_creates_expected_text_files(self) -> None:
        goog_feed = {
            "creationTime": "2026-04-01T00:00:00Z",
            "prefixes": [
                {"ipv4Prefix": "8.8.8.0/24"},
                {"ipv4Prefix": "34.0.0.0/24"},
                {"ipv6Prefix": "2001:4860::/32"},
            ],
        }
        cloud_feed = {
            "creationTime": "2026-04-01T00:05:00Z",
            "prefixes": [{"ipv4Prefix": "34.0.0.0/24"}],
        }
        apple_ranges = AppleRanges(ipv4=("17.0.0.0/8",), ipv6=("2620:149::/32",))
        cloudflare_ranges = CloudflareRanges(ipv4=("173.245.48.0/20",), ipv6=("2400:cb00::/32",))

        bundle = build_allowlists(
            goog_feed=goog_feed,
            cloud_feed=cloud_feed,
            apple_ranges=apple_ranges,
            cloudflare_ranges=cloudflare_ranges,
        )

        self.assertEqual(bundle.text_files["google_owned_ipv4.txt"], ("8.8.8.0/24", "34.0.0.0/24"))
        self.assertEqual(bundle.text_files["google_services_minus_cloud_ipv4.txt"], ("8.8.8.0/24",))
        self.assertEqual(bundle.text_files["apple_owned_ipv4.txt"], ("17.0.0.0/8",))
        self.assertEqual(bundle.text_files["cloudflare_proxy_ipv4.txt"], ("173.245.48.0/20",))
        self.assertIn("combined_google_services_plus_apple_plus_cloudflare_ipv6.txt", bundle.text_files)
        self.assertEqual(bundle.metadata["sources"]["google"]["goog_creation_time"], "2026-04-01T00:00:00Z")
        self.assertEqual(bundle.metadata["counts"]["cloudflare_proxy_ipv4_prefixes"], 1)

    def test_apple_ranges_can_be_loaded_from_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "apple-ranges.json"
            path.write_text(
                json.dumps({"ipv4": ["17.0.0.0/8"], "ipv6": ["2a01:b740::/32"]}),
                encoding="utf-8",
            )

            loaded = AppleRanges.from_file(path)

            self.assertEqual(loaded.ipv4, ("17.0.0.0/8",))
            self.assertEqual(loaded.ipv6, ("2a01:b740::/32",))

    def test_apple_ranges_from_mapping_accepts_single_string_values(self) -> None:
        loaded = AppleRanges.from_mapping({"ipv4": "17.0.0.0/8"})

        self.assertEqual(loaded.ipv4, ("17.0.0.0/8",))
        self.assertEqual(loaded.ipv6, ())

    def test_apple_ranges_from_mapping_rejects_non_string_iterables(self) -> None:
        with self.assertRaises(ValueError):
            AppleRanges.from_mapping({"ipv4": [17]})

    @mock.patch("google_apple_whitelist.core.fetch_text")
    @mock.patch("google_apple_whitelist.core.fetch_json")
    def test_run_fetch_writes_metadata_and_text_files(
        self,
        mock_fetch_json: mock.Mock,
        mock_fetch_text: mock.Mock,
    ) -> None:
        mock_fetch_json.side_effect = [
            {"creationTime": "goog-time", "prefixes": [{"ipv4Prefix": "8.8.8.0/24"}]},
            {"creationTime": "cloud-time", "prefixes": []},
        ]
        mock_fetch_text.side_effect = ["173.245.48.0/20\n", "2400:cb00::/32\n"]

        with tempfile.TemporaryDirectory() as tmp:
            summary = run_fetch(output_dir=Path(tmp), apple_ranges=AppleRanges(ipv4=("17.0.0.0/8",), ipv6=()))
            metadata = json.loads((Path(tmp) / "metadata.json").read_text(encoding="utf-8"))
            google_owned = (Path(tmp) / "google_owned_ipv4.txt").read_text(encoding="utf-8")
            cloudflare_txt = (Path(tmp) / "cloudflare_proxy_ipv4.txt").read_text(encoding="utf-8")

        self.assertEqual(summary.goog_creation_time, "goog-time")
        self.assertEqual(summary.cloud_creation_time, "cloud-time")
        self.assertIsNotNone(summary.cloudflare_retrieved_at)
        self.assertEqual(metadata["sources"]["google"]["cloud_creation_time"], "cloud-time")
        self.assertEqual(google_owned, "8.8.8.0/24\n")
        self.assertEqual(cloudflare_txt, "173.245.48.0/20\n")

    def test_write_allowlists_overwrites_files_atomically(self) -> None:
        bundle = build_allowlists(
            goog_feed={"creationTime": "g", "prefixes": [{"ipv4Prefix": "8.8.8.0/24"}]},
            cloud_feed={"creationTime": "c", "prefixes": []},
            apple_ranges=AppleRanges(ipv4=("17.0.0.0/8",), ipv6=()),
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            target = output_dir / "google_owned_ipv4.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("old\n", encoding="utf-8")
            write_allowlists(output_dir, bundle)

            self.assertEqual(target.read_text(encoding="utf-8"), "8.8.8.0/24\n")
