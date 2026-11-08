"""Round-trip latency to Polymarket's trading API from wherever this runs (read-only GET /time, keep-alive)."""
import time, statistics, socket, requests, json
S = requests.Session()
for host, path in (("https://clob.polymarket.com", "/time"), ("https://gamma-api.polymarket.com", "/events?limit=1")):
    S.get(host + path, timeout=10)  # warm TLS
    t = []
    for _ in range(15):
        a = time.perf_counter(); S.get(host + path, timeout=10); t.append((time.perf_counter() - a) * 1000)
    print(f"{host:38} keep-alive GET: median {statistics.median(t):6.1f} ms  min {min(t):6.1f} ms")
    cold = []
    for _ in range(3):
        a = time.perf_counter(); requests.get(host + path, timeout=10); cold.append((time.perf_counter() - a) * 1000)
    print(f"{'':38} new connection : median {statistics.median(cold):6.1f} ms (TLS handshake included)")
try:
    ip = requests.get("https://api.ipify.org", timeout=5).text
    print("public ip", ip, "geoblock:", requests.get("https://polymarket.com/api/geoblock", timeout=10).text[:120])
except Exception as e:
    print("ip/geoblock check failed", str(e)[:80])
