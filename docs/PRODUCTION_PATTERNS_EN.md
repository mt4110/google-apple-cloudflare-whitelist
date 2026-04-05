# Production Patterns

## Pattern A: Put your origin behind Cloudflare

### Goal

- Only let Cloudflare reach the origin
- Still expose the real client IP to the application safely

### Steps

1. Run `fetch` to retrieve `cloudflare_proxy_*.txt`
2. Run `render` to build `rendered_assets/nginx/cloudflare_real_ip.conf` and `cloudflare_origin_allow.conf`
3. In nginx:
   - `set_real_ip_from ...`
   - `real_ip_header CF-Connecting-IP`
   - `allow ... / deny all`
4. In the app, trust `CF-Connecting-IP` **only when the request actually came from Cloudflare**

### Reference files

- `examples/nginx/server-cloudflare-origin.conf`
- `examples/backend/validate_source_ip.py`
- `examples/ip_matching/README.md`

## Pattern B: Use Google + Apple as an egress allowlist helper

### Goal

- Coarsely allow egress in an internal firewall / proxy / policy engine
- While accepting that Apple coverage is intentionally incomplete

### Recommended datasets

- `combined_google_services_plus_apple_ipv4.txt`
- `combined_google_services_plus_apple_ipv6.txt`

### Steps

1. `fetch`
2. `render`
3. Apply `rendered_assets/ipset/*.restore` or `rendered_assets/nftables/*.nft`

### Reference files

- `examples/ipset/sync_whitelist_ipset.sh`
- `examples/nftables/main.nft`

## Pattern C: Statistical use

### Goal

- Log analysis
- Traffic labeling
- Rough classification

### Recommended datasets

- `combined_google_services_plus_apple_plus_cloudflare_ipv4.txt`
- `combined_google_services_plus_apple_plus_cloudflare_ipv6.txt`

### Warning

This is **not for authentication**.  
Use it when you want to say "this traffic probably belongs to this provider group."

## Minimal backend flow

```python
from google_apple_whitelist.matching import is_ip_in_networks, resolve_effective_client_ip

candidate_client_ip = resolve_effective_client_ip(
    remote_addr=remote_addr,
    forwarded_ip=request.headers.get("CF-Connecting-IP"),
    trusted_proxy_networks=cloudflare_proxy_ranges,
)

# The allowlist is only one layer here
if not is_ip_in_networks(candidate_client_ip, provider_ranges):
    reject()

# Production should not stop here
validate_token_or_signature()
```

## Things to avoid

- Treating Cloudflare IPs as end-user identity
- Treating Apple coarse CIDRs as a complete Apple inventory
- Reusing statistical union files for authentication
