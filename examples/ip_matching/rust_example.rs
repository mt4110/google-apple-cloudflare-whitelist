use ipnet::IpNet;
use std::fs;
use std::net::IpAddr;

fn load_nets(path: &str) -> Vec<IpNet> {
    fs::read_to_string(path)
        .expect("read failed")
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .map(|line| line.parse::<IpNet>().expect("invalid CIDR"))
        .collect()
}

fn is_apple_whitelist_ip(candidate_ip: &str, networks: &[IpNet]) -> bool {
    let ip: IpAddr = candidate_ip.parse().expect("invalid IP");
    networks.iter().any(|network| network.contains(&ip))
}

fn has_apple_whitelist_cidr(candidate_cidr: &str, networks: &[IpNet]) -> bool {
    let candidate: IpNet = candidate_cidr.parse().expect("invalid CIDR");
    networks.iter().any(|network| *network == candidate)
}

fn main() {
    let mut networks = load_nets("./whitelist_output/apple_owned_ipv4.txt");
    networks.extend(load_nets("./whitelist_output/apple_owned_ipv6.txt"));

    println!("{}", is_apple_whitelist_ip("17.10.20.30", &networks));
    println!("{}", is_apple_whitelist_ip("8.8.8.8", &networks));
    println!("{}", has_apple_whitelist_cidr("17.0.0.0/8", &networks));
    println!("{}", has_apple_whitelist_cidr("17.0.0.0/16", &networks));
}
