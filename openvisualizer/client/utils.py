def transform_into_ipv6(ipv6_str):
    for i in range(16):
        if i % 2 == 0:
            ipv6_str = ipv6_str.replace('-', '', 1)
        else:
            ipv6_str = ipv6_str.replace('-', ':', 1)
    return ipv6_str.strip()
