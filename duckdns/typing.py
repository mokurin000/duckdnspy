from enum import Enum


class IPV4(Enum):
    IPIP_NET = 1
    IPIFY = 2
    PROC = 3


class IPV6(Enum):
    PROC = 1
    IPIP_NET = 2
