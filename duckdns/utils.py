from logging import Logger
from ipaddress import IPv4Address

import aiohttp
import aiofiles
from aiohttp import ClientTimeout

logger = Logger(name=__name__)


async def clean_and_update_record(
    token: str,
    domains: str,
    ipv4: list[str] | None = None,
    ipv6: list[str] | None = None,
):
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
        logger.info(f"GET to {query_url}")
        async with session.get(query_url, timeout=ClientTimeout(total=10)) as resp:
            print(await resp.text())


async def extract_if_inet6(remove_lan: bool = True, skip_wlan=True):
    def grouper(iterable, n):
        "Collect data into non-overlapping fixed-length chunks or blocks."
        iterators = [iter(iterable)] * n
        return zip(*iterators, strict=True)

    ipv6 = []
    async with aiofiles.open("/proc/net/if_inet6", "r", encoding="utf-8") as file:
        content: str = await file.read()
        for line in content.split("\n"):
            if not line:
                continue
            if remove_lan and line.startswith("f"):
                continue
            if skip_wlan and line.split()[-1].startswith("wlan"):
                continue
            if line.split()[-1] == "lo":
                continue

            raw_hex, _, _, _, _, interface = line.split()
            v6addr = ":".join(map(lambda t: "".join(t), grouper(raw_hex, n=4)))
            ipv6.append(v6addr)

    return ipv6


async def extract_fib_trie_data(remove_lan: bool = True):
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
        filter(lambda ip: (not remove_lan) or IPv4Address(ip).is_global, results)
    )
