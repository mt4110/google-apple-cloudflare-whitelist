# Changelog

## 0.4.0

- added official Python IP/CIDR matching helpers in `src/google_apple_whitelist/matching.py`
- added `is_apple_whitelist_ip()` and `has_apple_whitelist_cidr()` as first-class package APIs
- added language examples for Python, TypeScript / Node.js, Go, and Rust under `examples/ip_matching/`
- updated backend example to use the official matching helpers
- documented the difference between IP membership and exact CIDR matching in both READMEs
- kept the Apple coverage language explicit: coarse ranges only, defensive / statistical use only

## 0.3.0

- added Cloudflare feed support to the main fetch flow
- added `render` subcommand for nginx / ipset / nftables helper files
- added practical docs for production patterns and design constraints
- added backend and infrastructure examples
- added release zip build / replacement scripts
- documented that Apple coverage is intentionally incomplete and that combined union files with Cloudflare are for statistical use

## 0.2.0

- added cross-platform scheduler examples
- added `mise` setup docs for macOS and Windows
- added CI and tests

## 0.1.0

- initial Google + Apple allowlist fetcher
