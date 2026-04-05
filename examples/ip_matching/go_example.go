package main

import (
    "bufio"
    "fmt"
    "net/netip"
    "os"
    "strings"
)

func loadPrefixes(path string) ([]netip.Prefix, error) {
    file, err := os.Open(path)
    if err != nil {
        return nil, err
    }
    defer file.Close()

    prefixes := make([]netip.Prefix, 0)
    scanner := bufio.NewScanner(file)
    for scanner.Scan() {
        line := strings.TrimSpace(scanner.Text())
        if line == "" {
            continue
        }
        prefix, err := netip.ParsePrefix(line)
        if err != nil {
            return nil, err
        }
        prefixes = append(prefixes, prefix.Masked())
    }
    return prefixes, scanner.Err()
}

func isAppleWhitelistIP(candidateIP string, prefixes []netip.Prefix) (bool, error) {
    addr, err := netip.ParseAddr(candidateIP)
    if err != nil {
        return false, err
    }
    for _, prefix := range prefixes {
        if prefix.Contains(addr) {
            return true, nil
        }
    }
    return false, nil
}

func hasAppleWhitelistCIDR(candidateCIDR string, prefixes []netip.Prefix) (bool, error) {
    candidate, err := netip.ParsePrefix(candidateCIDR)
    if err != nil {
        return false, err
    }
    candidate = candidate.Masked()
    for _, prefix := range prefixes {
        if prefix == candidate {
            return true, nil
        }
    }
    return false, nil
}

func main() {
    ipv4, err := loadPrefixes("./whitelist_output/apple_owned_ipv4.txt")
    if err != nil {
        panic(err)
    }
    ipv6, err := loadPrefixes("./whitelist_output/apple_owned_ipv6.txt")
    if err != nil {
        panic(err)
    }
    prefixes := append(ipv4, ipv6...)

    ok, _ := isAppleWhitelistIP("17.10.20.30", prefixes)
    fmt.Println(ok)
    ok, _ = isAppleWhitelistIP("8.8.8.8", prefixes)
    fmt.Println(ok)

    exact, _ := hasAppleWhitelistCIDR("17.0.0.0/8", prefixes)
    fmt.Println(exact)
    exact, _ = hasAppleWhitelistCIDR("17.0.0.0/16", prefixes)
    fmt.Println(exact)
}
