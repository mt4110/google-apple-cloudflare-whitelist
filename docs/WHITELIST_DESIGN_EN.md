# Whitelist Design

## Summary

This project builds **operationally useful allowlist inputs from public IP information**.  
It does **not** attempt to produce a perfect, exhaustive IP inventory.

## Source model

### Google

- `goog.json`
- `cloud.json`

Google publishes public feeds, but some use cases are better served by narrower crawler / fetcher feeds.  
This project uses `goog.json` and `cloud.json` as a **general-purpose base layer**.

### Apple

Apple publishes practical **coarse CIDRs**, but not a complete service-specific IP inventory.  
So Apple data is treated as a **maintained allowlist input**, not as a complete catalog.

### Cloudflare

Cloudflare publishes the IP ranges that reach your origin.  
Those ranges identify **Cloudflare edge nodes**, not the real end-user on their own.

## Principles used here

1. Use **publicly available inputs**
2. Prefer **updatable JSON / txt inputs** over hard-coded assumptions
3. **Do not pretend to be exhaustive**
4. Separate **statistical / defensive use** from **authentication use**
5. Keep the output easy to pair with **OS schedulers** and real infrastructure

## What this can and cannot do

### Can do

- Periodically fetch public Google / Apple / Cloudflare inputs
- Keep IPv4 and IPv6 separate
- Render helper files for `nftables`, `ipset`, and `nginx`
- Make statistical and defensive filtering easier to operate

### Cannot do

- Produce a complete Apple IP inventory
- Fully identify App Store-specific IPs
- Identify the real end-user from Cloudflare IPs alone
- Turn IP allowlisting into strict authentication by itself

## Recommended layers

### Layer 1: IP allowlist

- First-pass noise reduction
- Coarse ingress control

### Layer 2: reverse proxy / header validation

- For Cloudflare, trust `CF-Connecting-IP`
- But only when the request actually came from Cloudflare IP space

### Layer 3: application-level validation

- token
- signature
- mTLS
- application auth

## Output selection

### Strict origin ingress

- `cloudflare_proxy_ipv4.txt`
- `cloudflare_proxy_ipv6.txt`

### Practical Google + Apple allowlist helper

- `combined_google_services_plus_apple_ipv4.txt`
- `combined_google_services_plus_apple_ipv6.txt`

### Statistical / observational union

- `combined_google_services_plus_apple_plus_cloudflare_ipv4.txt`
- `combined_google_services_plus_apple_plus_cloudflare_ipv6.txt`

That final union is for **statistics**, not for strict authentication.

## Source links

- Google public IP ranges: `https://www.gstatic.com/ipranges/goog.json`
- Google Cloud external IP ranges: `https://www.gstatic.com/ipranges/cloud.json`
- Apple enterprise network guidance: `https://support.apple.com/en-us/101555`
- Cloudflare IP ranges: `https://www.cloudflare.com/ips/`
