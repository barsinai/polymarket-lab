"""Pin Polymarket traffic to IPv6 when the host has both (env PM_PREFER_IPV6=1, default on).

Why: Polymarket geoblocks by IP. Our pilot server's IPv4 sits in a range whose geolocation is stale
(mapped to Germany, a blocked country) while its IPv6 is mapped correctly (Finland). Every Polymarket
endpoint has IPv6, so we resolve *.polymarket.com to IPv6 addresses only; everything else is untouched.
Import this module before any HTTP library is used.
"""
import os, socket

_real = socket.getaddrinfo
_SUFFIXES = (".polymarket.com", "polymarket.com")


def _prefer6(host, port, family=0, type=0, proto=0, flags=0):
    res = _real(host, port, family, type, proto, flags)
    if isinstance(host, str) and host.endswith(_SUFFIXES) and family in (0, socket.AF_UNSPEC):
        v6 = [r for r in res if r[0] == socket.AF_INET6]
        if v6:
            return v6
    return res


if os.environ.get("PM_PREFER_IPV6", "1") == "1":
    socket.getaddrinfo = _prefer6


def geoblock_check():
    """Polymarket's own verdict for this machine, through the same resolver the bot uses."""
    import requests
    r = requests.get("https://polymarket.com/api/geoblock", timeout=20)
    r.raise_for_status()
    return r.json()
