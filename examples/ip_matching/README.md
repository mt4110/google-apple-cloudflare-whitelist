# IP matching examples

このディレクトリは、`whitelist_output/apple_owned_ipv4.txt` と `whitelist_output/apple_owned_ipv6.txt` を使って、

- **IP が Apple allowlist に入るか**
- **CIDR が Apple allowlist にそのまま存在するか**

を判定する最小例をまとめたものです。

大事なのは、この 2 つが別物だということです。

- `17.10.20.30` は **IP**
- `17.0.0.0/8` は **CIDR**

つまり:

- `isAppleWhiteList("17.10.20.30") == true`
- `hasAppleWhitelistCidr("17.0.0.0/8") == true`

は両立しますが、意味は違います。

## Important note

Apple ranges in this project are **coarse Apple-owned ranges**, not a complete App Store-specific inventory.
Use them for **defensive / statistical filtering**, not as a perfect identity proof.

## Files

- `python_example.py`
- `node_example.ts`
- `go_example.go`
- `rust_example.rs`

## Python

The repository now ships official helpers in `src/google_apple_whitelist/matching.py`:

- `is_apple_whitelist_ip(...)`
- `has_apple_whitelist_cidr(...)`
- `load_apple_whitelist_networks(...)`
- `resolve_effective_client_ip(...)`

## TypeScript / Node.js

This example uses `ipaddr.js` to avoid re-implementing IPv4 / IPv6 CIDR parsing.

```bash
npm install ipaddr.js
```

## Go

The Go example uses only the standard library (`net/netip`).

## Rust

The Rust example uses the widely used `ipnet` crate.

```bash
cargo add ipnet
```
