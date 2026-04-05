import fs from "node:fs";
import ipaddr from "ipaddr.js";

function loadCidrs(path: string): string[] {
  return fs
    .readFileSync(path, "utf8")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function isAppleWhitelistIp(candidateIp: string, cidrs: string[]): boolean {
  const candidate = ipaddr.parse(candidateIp);
  return cidrs.some((cidr) => {
    const [network, prefixLength] = ipaddr.parseCIDR(cidr);
    return candidate.kind() === network.kind() && candidate.match([network, prefixLength]);
  });
}

function hasAppleWhitelistCidr(candidateCidr: string, cidrs: string[]): boolean {
  return cidrs.includes(candidateCidr);
}

const cidrs = [
  ...loadCidrs("./whitelist_output/apple_owned_ipv4.txt"),
  ...loadCidrs("./whitelist_output/apple_owned_ipv6.txt"),
];

console.log(isAppleWhitelistIp("17.10.20.30", cidrs));
console.log(isAppleWhitelistIp("8.8.8.8", cidrs));
console.log(hasAppleWhitelistCidr("17.0.0.0/8", cidrs));
console.log(hasAppleWhitelistCidr("17.0.0.0/16", cidrs));
