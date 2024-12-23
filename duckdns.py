import sys
import json
import asyncio
import tomllib
from os import environ
from enum import Enum
from platform import system
from ipaddress import IPv4Address

import aiohttp
import aiofiles
from aiohttp import ClientTimeout


REMOVE_LAN_IP = environ.get("REMOVE_LAN_IP", "1") == "1"


def grouper(iterable, n):
    "Collect data into non-overlapping fixed-length chunks or blocks."
    iterators = [iter(iterable)] * n
    return zip(*iterators, strict=True)


class IPV4(Enum):
    IPIP_NET = 1
    IPIFY = 2
    PROC = 3


class IPV6(Enum):
    PROC = 1
    IPIP_NET = 2


async def extract_if_inet6():
    ipv6 = []
    async with aiofiles.open("/proc/net/if_inet6", "r", encoding="utf-8") as file:
        content: str = await file.read()
        for line in content.split("\n"):
            if not line:
                continue
            if REMOVE_LAN_IP and line.startswith("fe80"):
                continue
            if REMOVE_LAN_IP and line.endswith("lo"):
                continue

            raw_hex, _, _, _, _, interface = line.split()
            v6addr = ":".join(map(lambda t: "".join(t), grouper(raw_hex, n=4)))
            ipv6.append(v6addr)

    return ipv6


async def extract_fib_trie_data():
    async with aiofiles.open("/proc/net/fib_trie", "r", encoding="utf-8") as file:
        lines = await file.readlines()

    results = set()

    f = None

    for line in lines:
        fields = line.strip().split()

        if "32 host" in line:
            if f is not None:
                results.add(f)

        if len(fields) > 1 and fields[1]:
            f = fields[1]

    return sorted(
        filter(lambda ip: (not REMOVE_LAN_IP) or IPv4Address(ip).is_global, results)
    )


async def get_ip(
    session: aiohttp.ClientSession, v4_source: IPV4, v6_source: IPV6
) -> tuple[list[str] | None, list[str] | None]:
    match v4_source:
        case IPV4.IPIFY:
            async with session.get("https://api.ipify.org/?format=json") as resp:
                data: dict[str, str] = await resp.json()
                ipv4 = [data.get("ip", None)]

        case IPV4.IPIP_NET:
            async with session.get("https://myip.ipip.net/") as resp:
                data: str = await resp.text()
                ipv4 = [data.removeprefix("当前 IP：").split()[0]]

        case IPV4.PROC:
            ipv4 = await extract_fib_trie_data()

        case _:
            ipv4 = None

    match v6_source:
        case IPV6.PROC:
            ipv6 = await extract_if_inet6()
        case IPV6.IPIP_NET:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(verify_ssl=False)
            ) as insecure_session:
                async with insecure_session.get(
                    "https://myip6.ipip.net/",
                ) as resp:
                    data: str = await resp.text()
                    ipv6 = [data.removeprefix("当前 IP：").split()[0]]

    return ipv4, ipv6


async def main():
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

    query_url = (
        f"https://www.duckdns.org/update?domains={domains}&token={token}&verbose=true"
    )
    if ipv4:
        query_url += f"&ip={ipv4[0]}"
    if ipv6:
        query_url += f"&ipv6={ipv6[0]}"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{query_url}&clear=true", timeout=ClientTimeout(total=10)
        ):
            pass
        async with session.get(query_url, timeout=ClientTimeout(total=10)) as resp:
            print(await resp.text())

    for domain in domains.split(","):
        print(f"{domain}.duckdns.org")


if __name__ == "__main__":
    asyncio.run(main())
