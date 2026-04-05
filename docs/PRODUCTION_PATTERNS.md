# Production Patterns

## Pattern A: Cloudflare の後ろに origin を置く

### 目的

- origin へは Cloudflare からしか到達させない
- ただしアプリでは元クライアント IP を扱いたい

### 手順

1. `fetch` で `cloudflare_proxy_*.txt` を取得
2. `render` で `rendered_assets/nginx/cloudflare_real_ip.conf` と `cloudflare_origin_allow.conf` を生成
3. nginx で:
   - `set_real_ip_from ...`
   - `real_ip_header CF-Connecting-IP`
   - `allow ... / deny all`
4. アプリでは **Cloudflare IP から来たときだけ** `CF-Connecting-IP` を信頼する

### 参考ファイル

- `examples/nginx/server-cloudflare-origin.conf`
- `examples/backend/validate_source_ip.py`
- `examples/ip_matching/README.md`

## Pattern B: egress allowlist として Google + Apple を使う

### 目的

- 社内 FW / proxy / egress policy で coarse に許可したい
- ただし Apple は完全ではないことを理解した上で使う

### 推奨データ

- `combined_google_services_plus_apple_ipv4.txt`
- `combined_google_services_plus_apple_ipv6.txt`

### 使い方

1. `fetch`
2. `render`
3. `rendered_assets/ipset/*.restore` または `rendered_assets/nftables/*.nft` を適用

### 参考ファイル

- `examples/ipset/sync_whitelist_ipset.sh`
- `examples/nftables/main.nft`

## Pattern C: 統計的利用

### 目的

- ログ分析
- 流量のラベル付け
- 大ざっぱな分類

### 推奨データ

- `combined_google_services_plus_apple_plus_cloudflare_ipv4.txt`
- `combined_google_services_plus_apple_plus_cloudflare_ipv6.txt`

### 注意

これは **認証用ではない** です。  
「この通信はたぶんこの provider 群っぽい」を寄せる用途です。

## バックエンドでの最低限の考え方

```python
from google_apple_whitelist.matching import is_ip_in_networks, resolve_effective_client_ip

candidate_client_ip = resolve_effective_client_ip(
    remote_addr=remote_addr,
    forwarded_ip=request.headers.get("CF-Connecting-IP"),
    trusted_proxy_networks=cloudflare_proxy_ranges,
)

# ここで allowlist は 1 レイヤーとして使う
if not is_ip_in_networks(candidate_client_ip, provider_ranges):
    reject()

# でも本番ではここで終わらない
validate_token_or_signature()
```

## 避けたほうがいいこと

- Cloudflare の IP だけでユーザー本人確認をしたことにする
- Apple の coarse CIDR を「完全な Apple IP」と扱う
- 統計用 union を認証用途へ流用する
