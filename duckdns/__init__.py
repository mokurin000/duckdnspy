import aiohttp

from duckdns.model import IPV4, IPV6
from duckdns.utils import extract_fib_trie_data, extract_if_inet6

from os import environ

REMOVE_LAN_IP = environ.get("REMOVE_LAN_IP", "1") == "1"


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
            ipv4 = await extract_fib_trie_data(remove_lan=REMOVE_LAN_IP)

        case _:
            ipv4 = None

    match v6_source:
        case IPV6.PROC:
            ipv6 = await extract_if_inet6(remove_lan=REMOVE_LAN_IP)
        case IPV6.IPIP_NET:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False)
            ) as insecure_session:
                async with insecure_session.get(
                    "https://myip6.ipip.net/",
                ) as resp:
                    data: str = await resp.text()
                    ipv6 = [data.removeprefix("当前 IP：").split()[0]]

    return ipv4, ipv6
