import sys
import json
import asyncio
import tomllib
from platform import system

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

    await clean_and_update_record(token=token, domains=domains, ipv4=ipv4, ipv6=ipv6)

    for domain in domains.split(","):
        print(f"{domain}.duckdns.org")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
