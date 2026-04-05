# Whitelist Design

## 要旨

このプロジェクトは、**公開されている IP 情報だけを使って、実務で扱える allowlist の材料を作る** ためのものです。  
ただし、**完全な IP 一覧を作ること** は目的でもなければ、現実的でもありません。

## ソースの考え方

### Google

- `goog.json`
- `cloud.json`

Google は公開 feed を提供しています。  
ただし、用途によっては crawler / fetcher 専用の feed を使うほうが正確です。  
このプロジェクトでは **一般用途向けの土台** として `goog.json` と `cloud.json` を扱います。

### Apple

Apple は実務で使える **coarse CIDR** は公開していますが、**完全なサービス別 IP 一覧** は公開していません。  
したがって、Apple 側は **「設定可能な allowlist 入力」** として扱います。

### Cloudflare

Cloudflare は origin へ到達するための IP ranges を公開しています。  
ただし、これは **Cloudflare edge の IP** であって、**元クライアント本人の IP を意味しません**。

## ここで守っている原則

1. **公開情報だけを使う**
2. **固定値より JSON / txt を優先して更新可能にする**
3. **完全性を装わない**
4. **統計的 / 防御的利用と、認証用途を明確に分ける**
5. **OS のスケジューラと組み合わせやすい形にする**

## 何が「できる」で、何が「できない」か

### できる

- Google / Apple / Cloudflare の公開情報を定期取得する
- IPv4 / IPv6 を分けて出す
- `nftables` / `ipset` / `nginx` 用の補助ファイルを生成する
- 統計的・運用的に「このへんを通す / 寄せる」をやりやすくする

### できない

- Apple の完全な IP 一覧を作る
- App Store 専用 IP を完全に識別する
- Cloudflare の IP だけで元クライアント本人を特定する
- IP allowlist だけで厳密な認証を成立させる

## 推奨レイヤー

### Layer 1: IP allowlist

- 最初のノイズ削減
- coarse な入口制御

### Layer 2: reverse proxy / header validation

- Cloudflare なら `CF-Connecting-IP`
- ただし **Cloudflare IP から来た時だけ** 信頼する

### Layer 3: application-level validation

- token
- signature
- mTLS
- application auth

## 出力の使い分け

### 厳しめの origin 制御

- `cloudflare_proxy_ipv4.txt`
- `cloudflare_proxy_ipv6.txt`

### Google + Apple の allowlist 補助

- `combined_google_services_plus_apple_ipv4.txt`
- `combined_google_services_plus_apple_ipv6.txt`

### 統計・観測寄り

- `combined_google_services_plus_apple_plus_cloudflare_ipv4.txt`
- `combined_google_services_plus_apple_plus_cloudflare_ipv6.txt`

この最後の union は、**認証用ではなく統計用** です。

## 根拠リンク

- Google public IP ranges: `https://www.gstatic.com/ipranges/goog.json`
- Google Cloud external IP ranges: `https://www.gstatic.com/ipranges/cloud.json`
- Apple enterprise network guidance: `https://support.apple.com/en-us/101555`
- Cloudflare IP ranges: `https://www.cloudflare.com/ips/`
