import sys
import json
import asyncio
import tomllib
from platform import system
from ipaddress import IPv6Address

import aiohttp
import aiofiles

from duckdns import get_ip
from duckdns.model import IPV6
from duckdns.utils import (
    clean_and_update_record,
)


async def run():
    if system() == "Linux":
        ipv6_method = IPV6.PROC
    else:
        ipv6_method = IPV6.IPIP_NET

    async with aiohttp.ClientSession() as session:
        ipv4, ipv6 = await get_ip(
            session=session, v4_source=None, v6_source=ipv6_method
        )

    obj = {"ipv4": ipv4, "ipv6": ipv6}
    json_output = json.dumps(obj=obj, indent=4, ensure_ascii=False)
    print(json_output, file=sys.stderr)

    async with aiofiles.open("config.toml") as f:
        config = tomllib.loads(await f.read())

    domains: str = config.get("domains")
    token: str = config.get("token")
    fixed_v6_suffix: str = config.get("fixed-v6-suffix")

    if fixed_v6_suffix and ipv6:
        ipv6_addr = IPv6Address(ipv6[0])
        origin_addr = ipv6_addr.exploded.replace(":", "")
        suffix, length = fixed_v6_suffix.split("/")

        length = int(length)
        part_len = -length // 4

        prefix = origin_addr[: 32 - part_len] + part_len * "0"
        suffix_addr = IPv6Address(suffix).exploded.replace(":", "")
        result_addr = sum(map(lambda x: int(x, base=16), [prefix, suffix_addr]))
        result_addr = IPv6Address(result_addr)
        ipv6 = [result_addr]

    await clean_and_update_record(token=token, domains=domains, ipv4=ipv4, ipv6=ipv6)

    for domain in domains.split(","):
        print(f"{domain}.duckdns.org")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
