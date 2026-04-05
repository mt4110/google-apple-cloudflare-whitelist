from __future__ import annotations

from pathlib import Path

from google_apple_whitelist.matching import (
    has_apple_whitelist_cidr,
    is_apple_whitelist_ip,
)

whitelist_dir = Path("./whitelist_output")

print(is_apple_whitelist_ip("17.10.20.30", output_dir=whitelist_dir))
print(is_apple_whitelist_ip("8.8.8.8", output_dir=whitelist_dir))
print(has_apple_whitelist_cidr("17.0.0.0/8", output_dir=whitelist_dir))
print(has_apple_whitelist_cidr("17.0.0.0/16", output_dir=whitelist_dir))
