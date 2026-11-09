"""Polymarket real-time data feed (RTDS, wss://ws-live-data.polymarket.com): the Chainlink prices and the
60-second Chainlink TWAP that the crypto Up/Down markets resolve on. Read-only.

Runs as a background thread: keeps the latest values per symbol in memory and appends every message
(thinned to one per second per symbol/topic) to data/fast/rtds/<UTC hour>.jsonl.gz.
"""
import asyncio, gzip, json, os, threading, time
from collections import deque
from datetime import datetime, timezone

URL = "wss://ws-live-data.polymarket.com"
TOPICS = ("crypto_prices_chainlink", "crypto_prices_twap_sixty", "crypto_prices_twap_thirty", "crypto_prices")
D = os.environ.get("FAST_DIR", "data/fast") + "/rtds"
os.makedirs(D, exist_ok=True)

latest = {}                       # (topic, symbol) -> (ts_ms, value)
hist = {}                         # (topic, symbol) -> deque of (ts_s, value), last ~25 min
stats = {"msgs": 0, "connects": 0, "errors": 0, "last_msg": 0.0, "topics": {}}
_lock = threading.Lock()


def _store(topic, sym, ts_ms, val):
    key = (topic, sym)
    with _lock:
        latest[key] = (ts_ms, val)
        h = hist.setdefault(key, deque(maxlen=3000))
        if not h or ts_ms / 1000 - h[-1][0] >= 0.5:
            h.append((ts_ms / 1000, val))


def series(topic, sym, lo, hi):
    """(ts, value) points with lo <= ts < hi (seconds)"""
    with _lock:
        return [(t, v) for t, v in hist.get((topic, sym), ()) if lo <= t < hi]


def last(topic, sym):
    with _lock:
        return latest.get((topic, sym))


async def _run(stop):
    import websockets
    out = None; out_hour = None; thin = {}
    while not stop.is_set():
        try:
            async with websockets.connect(URL, ping_interval=None, max_size=2 ** 22) as ws:
                stats["connects"] += 1
                await ws.send(json.dumps({"action": "subscribe", "subscriptions": [{"topic": t, "type": "*"} for t in TOPICS]}))
                last_ping = time.time(); last_rx = time.time()
                while not stop.is_set():
                    if time.time() - last_ping > 5:
                        await ws.send("PING"); last_ping = time.time()
                        try:
                            await asyncio.wait_for(ws.ping(), timeout=5)
                        except Exception:  # noqa: BLE001
                            break   # protocol ping failed: reconnect
                    if time.time() - last_rx > 20:
                        stats["silent_reconnects"] = stats.get("silent_reconnects", 0) + 1
                        break       # the feed went quiet (seen after ~40 min): reconnect and re-subscribe
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=5)
                    except asyncio.TimeoutError:
                        continue
                    stats["msgs"] += 1; stats["last_msg"] = time.time(); last_rx = time.time()
                    if not isinstance(raw, str) or not raw.startswith("{"):
                        continue
                    try:
                        m = json.loads(raw)
                    except ValueError:
                        continue
                    topic = m.get("topic"); p = m.get("payload") or {}
                    stats["topics"][topic] = stats["topics"].get(topic, 0) + 1
                    sym = str(p.get("symbol", "")).lower(); val = p.get("value"); ts = p.get("timestamp") or m.get("timestamp")
                    if topic and sym and isinstance(val, (int, float)) and ts:
                        ts_ms = int(ts) if int(ts) > 10 ** 11 else int(ts) * 1000
                        _store(topic, sym, ts_ms, float(val))
                        k = (topic, sym); now = time.time()
                        if now - thin.get(k, 0) < 1.0:
                            continue
                        thin[k] = now
                    hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
                    if hour != out_hour:
                        if out:
                            out.close(); compress(out_hour)
                        out = open(f"{D}/{hour}.jsonl", "a"); out_hour = hour
                    out.write(json.dumps({"rx": round(time.time(), 3), "m": m}) + "\n")
        except Exception as e:  # noqa: BLE001
            stats["errors"] += 1; stats["last_error"] = str(e)[:160]
            await asyncio.sleep(3)
    if out:
        out.close(); compress(out_hour)


def compress(hour=None):
    """plain .jsonl while recording (a crash cannot corrupt it); finished hours become .jsonl.gz members,
    written to a temp file first so a crash never leaves a half-written archive"""
    import glob, shutil
    cur = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
    for f in sorted(glob.glob(f"{D}/*.jsonl")):
        h = os.path.basename(f)[:-6]
        if h == cur and hour != cur:
            continue
        gz, tmp = f"{D}/{h}.jsonl.gz", f"{D}/{h}.jsonl.gz.tmp"
        try:
            if os.path.exists(gz) and os.path.getsize(gz) > 0:
                shutil.copyfile(gz, tmp)
            with open(f) as src, gzip.open(tmp, "at") as dst:
                for line in src:
                    if line.endswith("\n") and line.startswith("{"):
                        dst.write(line)
            os.replace(tmp, gz); os.remove(f)
        except OSError:
            try:
                os.remove(tmp)
            except OSError:
                pass


def start():
    compress()
    stop = threading.Event()

    def runner():
        asyncio.run(_run(stop))
    threading.Thread(target=runner, daemon=True).start()
    return stop


if __name__ == "__main__":
    s = start()
    t_end = time.time() + float(os.environ.get("RUN_MIN", "2")) * 60
    while time.time() < t_end:
        time.sleep(10)
        print(json.dumps(stats), {k[0][14:] + ":" + k[1]: v for k, v in list(latest.items())[:12]}, flush=True)
    s.set(); time.sleep(1)
