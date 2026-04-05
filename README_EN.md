# Public IP Range Fetcher and Network Allowlist Generator

The CLI / package name stays `google-apple-whitelist` for compatibility.  
This repository aggregates **Google public IP feeds**, **Apple published coarse CIDRs**, and **Cloudflare origin IP ranges**, then generates helper files for network allowlist operations.

## What this is good for

- **Coarse ingress filtering** in firewalls, WAFs, and reverse proxies
- **Statistical grouping** of traffic that likely belongs to Google + Apple
- **Origin reachability control** when Cloudflare sits in front of your service
- Preparing inputs for `nftables`, `ipset`, and `nginx`

## What this is not

This tool is **not a perfect identification system**.

- **Apple does not publish a complete IP inventory**, so this project remains **coarse-range-based**
- **Cloudflare IPs identify Cloudflare edge nodes**, not the real end-user by themselves
- On the origin side, you must **validate forwarded headers before trusting them**
- **Google has multiple feed shapes depending on the use case**, so generic `goog.json` can be too broad
- This project is therefore intended for **defensive / statistical filtering**
- In production, combine it with **authentication, signatures, and header validation**

In other words:

> **IP allowlisting is one layer of control, not identity proof**

The rationale and constraints are documented here:

- English: [docs/WHITELIST_DESIGN_EN.md](docs/WHITELIST_DESIGN_EN.md)
- 日本語: [docs/WHITELIST_DESIGN.md](docs/WHITELIST_DESIGN.md)

Production patterns live here:

- English: [docs/PRODUCTION_PATTERNS_EN.md](docs/PRODUCTION_PATTERNS_EN.md)
- 日本語: [docs/PRODUCTION_PATTERNS.md](docs/PRODUCTION_PATTERNS.md)

## No Python installed? Use mise (recommended)

This repository ships with `mise.toml`, so you can run it even if Python is not installed globally.

### macOS

```bash
brew install mise
```

### Windows

```powershell
scoop install mise
```

Alternative:

```powershell
winget install jdx.mise
```

## Fast setup

```bash
git clone <your-repo-url>
cd google-apple-cloudflare-whitelist
mise trust
mise install
mise run fetch
mise run render
```

### Why `mise trust` is needed

On first run, you may see:

```text
Config files ... are not trusted.
```

Then run:

```bash
mise trust
```

If you want to trust multiple configs at once:

```bash
mise trust -a
```

## Use Python directly

### Requirements

- Python 3.10+

### Install for development

```bash
python -m pip install -e .
```

### Fetch once

```bash
PYTHONPATH=src python -m google_apple_whitelist fetch --output-dir ./whitelist_output
```

### Render nginx / ipset / nftables helper files from fetched txt files

```bash
PYTHONPATH=src python -m google_apple_whitelist render \
  --input-dir ./whitelist_output \
  --output-dir ./rendered_assets
```

### Override Apple ranges from an external JSON file

```bash
PYTHONPATH=src python -m google_apple_whitelist fetch \
  --output-dir ./whitelist_output \
  --apple-ranges-file ./apple_ranges.example.json
```

JSON shape:

```json
{
  "ipv4": ["17.0.0.0/8"],
  "ipv6": ["2403:300::/32", "2620:149::/32", "2a01:b740::/32"]
}
```

### Fetch without Cloudflare

```bash
PYTHONPATH=src python -m google_apple_whitelist fetch \
  --output-dir ./whitelist_output \
  --no-include-cloudflare
```

### Run refreshes in a Python loop

```bash
PYTHONPATH=src python -m google_apple_whitelist daemon \
  --output-dir ./whitelist_output \
  --interval-seconds 86400
```

That works, but for production, **OS schedulers are usually the cleaner choice**.

## Meaning of the output files

### `fetch` outputs

- `google_owned_ipv4.txt` / `google_owned_ipv6.txt`  
  Google-owned public feed
- `google_services_minus_cloud_ipv4.txt` / `google_services_minus_cloud_ipv6.txt`  
  `goog.json - cloud.json`
- `apple_owned_ipv4.txt` / `apple_owned_ipv6.txt`  
  Apple published coarse ranges
- `cloudflare_proxy_ipv4.txt` / `cloudflare_proxy_ipv6.txt`  
  Cloudflare-to-origin addresses
- `combined_google_services_plus_apple_*.txt`  
  A practical union for many allowlist workflows
- `combined_*_plus_cloudflare_*.txt`  
  Intended for **statistical union use only**, not strict authentication

### `render` outputs

- `rendered_assets/nginx/*.conf`
- `rendered_assets/ipset/*.restore`
- `rendered_assets/nftables/*.nft`

These make it easier to feed the fetched txt files into real infrastructure.

## IP matching helpers (official Python API)

The package now includes a dedicated module at `src/google_apple_whitelist/matching.py` for Apple allowlist checks.

- `is_apple_whitelist_ip("17.10.20.30", output_dir=Path("./whitelist_output"))`
- `has_apple_whitelist_cidr("17.0.0.0/8", output_dir=Path("./whitelist_output"))`

Use them for two different questions:

- **IP membership**: does `17.10.20.30` belong to `17.0.0.0/8`?
- **Exact CIDR match**: does the allowlist contain the exact CIDR `17.0.0.0/8`?

Minimal examples: [examples/ip_matching/README.md](examples/ip_matching/README.md)

```python
from pathlib import Path
from google_apple_whitelist.matching import (
    has_apple_whitelist_cidr,
    is_apple_whitelist_ip,
)

whitelist_dir = Path("./whitelist_output")

assert is_apple_whitelist_ip("17.10.20.30", output_dir=whitelist_dir) is True
assert has_apple_whitelist_cidr("17.0.0.0/8", output_dir=whitelist_dir) is True
```

## Practical examples included

### Schedulers

- `scripts/run_fetch.sh`
- `scripts/run_fetch.ps1`
- `examples/systemd/google-apple-whitelist.service`
- `examples/systemd/google-apple-whitelist.timer`
- `examples/cron/google-apple-whitelist.cron`
- `examples/macos/com.google-apple-whitelist.plist`
- `examples/windows/register-google-apple-whitelist-task.ps1`

### Network / proxy

- `examples/nginx/server-cloudflare-origin.conf`
- `examples/ipset/sync_whitelist_ipset.sh`
- `examples/nftables/main.nft`

### Backend example

- `examples/backend/validate_source_ip.py`
- `examples/ip_matching/README.md`
- `examples/ip_matching/python_example.py`
- `examples/ip_matching/node_example.ts`
- `examples/ip_matching/go_example.go`
- `examples/ip_matching/rust_example.rs`

## OS-specific scheduling

### Linux: systemd timer (recommended)

```bash
sudo cp examples/systemd/google-apple-whitelist.service /etc/systemd/system/
sudo cp examples/systemd/google-apple-whitelist.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now google-apple-whitelist.timer
```

Verify:

```bash
systemctl list-timers google-apple-whitelist.timer
journalctl -u google-apple-whitelist.service -f
```

### Linux: cron

```bash
crontab examples/cron/google-apple-whitelist.cron
```

### macOS: launchd

```bash
mkdir -p ~/Library/LaunchAgents
cp examples/macos/com.google-apple-whitelist.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.google-apple-whitelist.plist
launchctl kickstart -k gui/$(id -u)/com.google-apple-whitelist
```

### Windows: Task Scheduler

```powershell
PowerShell -ExecutionPolicy Bypass -File .\examples\windows\register-google-apple-whitelist-task.ps1 -RepoPath "$PWD"
```

## `whitelist_output` is gitignored

Generated files are environment-specific, so `whitelist_output/` and `rendered_assets/` are ignored by default.

## Building a release ZIP

### Build a clean ZIP from the current working tree

```bash
python ./scripts/build_release_zip.py --source-dir . --output ./dist/google-apple-whitelist-oss-complete.zip
```

### Replace the contents of an existing ZIP with the current working tree

```bash
python ./scripts/replace_zip_contents.py \
  --base-zip ./old-release.zip \
  --source-dir . \
  --output ./dist/google-apple-whitelist-oss-complete.zip
```

## Tests

```bash
mise run test
```

or:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```
