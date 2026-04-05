from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from google_apple_whitelist.rendering import build_nftables_snippet, render_artifacts


class RenderingTests(unittest.TestCase):
    def test_render_artifacts_builds_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "whitelist_output"
            output_dir = Path(tmp) / "rendered_assets"
            input_dir.mkdir(parents=True, exist_ok=True)
            (input_dir / "combined_google_services_plus_apple_ipv4.txt").write_text("8.8.8.0/24\n", encoding="utf-8")
            (input_dir / "combined_google_services_plus_apple_ipv6.txt").write_text("2001:4860::/32\n", encoding="utf-8")
            (input_dir / "cloudflare_proxy_ipv4.txt").write_text("173.245.48.0/20\n", encoding="utf-8")
            (input_dir / "cloudflare_proxy_ipv6.txt").write_text("2400:cb00::/32\n", encoding="utf-8")

            summary = render_artifacts(input_dir=input_dir, output_dir=output_dir)

            nginx_allow = (output_dir / "nginx" / "combined_google_services_plus_apple_allow.conf").read_text(encoding="utf-8")
            ipset_restore = (output_dir / "ipset" / "combined_google_services_plus_apple.restore").read_text(encoding="utf-8")
            nftables_snippet = (output_dir / "nftables" / "combined_google_services_plus_apple.nft").read_text(encoding="utf-8")
            cf_real_ip = (output_dir / "nginx" / "cloudflare_real_ip.conf").read_text(encoding="utf-8")

        self.assertEqual(summary.dataset, "combined_google_services_plus_apple")
        self.assertIn("allow 8.8.8.0/24;", nginx_allow)
        self.assertIn("deny all;", nginx_allow)
        self.assertIn("create gaw_allow_v4 hash:net family inet -exist", ipset_restore)
        self.assertIn("set gaw_allow_v4 {", nftables_snippet)
        self.assertIn("real_ip_header CF-Connecting-IP;", cf_real_ip)

    def test_render_artifacts_requires_dataset_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "whitelist_output"
            output_dir = Path(tmp) / "rendered_assets"
            input_dir.mkdir(parents=True, exist_ok=True)

            with self.assertRaises(FileNotFoundError):
                render_artifacts(input_dir=input_dir, output_dir=output_dir)

    def test_build_nftables_snippet_emits_valid_statement_terminators(self) -> None:
        snippet = build_nftables_snippet("gaw", ("8.8.8.0/24",), ("2001:4860::/32",))

        self.assertIn("type ipv4_addr;", snippet)
        self.assertIn("flags interval;", snippet)
        self.assertIn("    };\n}", snippet)
        self.assertIn("type ipv6_addr;", snippet)

    def test_render_artifacts_rejects_dataset_with_path_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp) / "whitelist_output"
            output_dir = Path(tmp) / "rendered_assets"
            input_dir.mkdir(parents=True, exist_ok=True)

            with self.assertRaises(ValueError):
                render_artifacts(input_dir=input_dir, output_dir=output_dir, dataset="../escape")
