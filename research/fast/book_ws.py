"""Real-time order-book recorder for the Up/Down markets (CLOB market websocket). Read-only.

Subscribes to the outcome tokens the bot says are active (last LAST_S seconds of each window), keeps a local
book per token from the 'book' snapshot + 'price_change' deltas, and appends every event with a receive
timestamp to data/fast/bookws/<UTC hour>.jsonl (compressed when the hour is over).
Purpose: measure how long a cheap ask on a locked outcome survives (milliseconds), which decides whether a
push-driven bot could ever reach it from here.
"""
import asyncio, gzip, json, os, threading, time
from datetime import datetime, timezone

URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
D = os.environ.get("FAST_DIR", "data/fast") + "/bookws"
os.makedirs(D, exist_ok=True)
books = {}          # asset_id -> {"bids": {price: size}, "asks": {price: size}, "ts": server_ms, "rx": float}
stats = {"msgs": 0, "connects": 0, "errors": 0, "subscribed": 0, "last_msg": 0.0}
_lock = threading.Lock()


def best(asset_id):
    """(best_ask_price, size), (best_bid_price, size) from the local book, or (None, None)"""
    with _lock:
        b = books.get(asset_id)
        if not b:
            return None, None
        asks = [(float(p), s) for p, s in b["asks"].items() if s > 0]
        bids = [(float(p), s) for p, s in b["bids"].items() if s > 0]
        return (min(asks) if asks else None), (max(bids) if bids else None)


def compress(hour=None):
    import glob
    cur = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
    for f in sorted(glob.glob(f"{D}/*.jsonl")):
        h = os.path.basename(f)[:-6]
        if h == cur and hour != cur:
            continue
        try:
            with open(f) as src, gzip.open(f"{D}/{h}.jsonl.gz", "at") as dst:
                for line in src:
                    if line.endswith("\n") and line.startswith("{"):
                        dst.write(line)
            os.remove(f)
        except OSError:
            pass


def _apply(m, rx):
    et = m.get("event_type")
    if et == "book":
        a = m.get("asset_id")
        with _lock:
            books[a] = {"bids": {x["price"]: float(x["size"]) for x in m.get("bids") or []},
                        "asks": {x["price"]: float(x["size"]) for x in m.get("asks") or []}, "ts": m.get("timestamp"), "rx": rx}
        return {"t": "book", "a": a, "ts": m.get("timestamp"), "bids": [[x["price"], x["size"]] for x in (m.get("bids") or [])[-12:]],
                "asks": [[x["price"], x["size"]] for x in (m.get("asks") or [])[-12:]]}
    if et == "price_change":
        out = []
        for c in m.get("price_changes") or []:
            a = c.get("asset_id"); side = "bids" if str(c.get("side")).upper() == "BUY" else "asks"
            with _lock:
                b = books.setdefault(a, {"bids": {}, "asks": {}, "ts": None, "rx": rx})
                b[side][c["price"]] = float(c["size"]); b["ts"] = m.get("timestamp"); b["rx"] = rx
            out.append([a, c.get("price"), c.get("size"), side[0], c.get("best_bid"), c.get("best_ask")])
        return {"t": "pc", "ts": m.get("timestamp"), "c": out}
    if et == "last_trade_price":
        return {"t": "ltp", "a": m.get("asset_id"), "ts": m.get("timestamp"), "p": m.get("price"), "s": m.get("size"), "side": m.get("side")}
    return None


async def _run(stop, active):
    import websockets
    out = None; out_hour = None; subscribed = set()
    while not stop.is_set():
        try:
            async with websockets.connect(URL, ping_interval=None, max_size=2 ** 23) as ws:
                stats["connects"] += 1; subscribed = set()
                want = set(active())
                if want:
                    await ws.send(json.dumps({"assets_ids": sorted(want), "type": "market"})); subscribed = set(want)
                last_ping = time.time(); last_rx = time.time(); last_sync = time.time()
                while not stop.is_set():
                    now = time.time()
                    if now - last_ping > 10:
                        await ws.send("PING"); last_ping = now
                    if now - last_sync > 2:
                        last_sync = now; want = set(active())
                        add, rem = want - subscribed, subscribed - want
                        if add:
                            await ws.send(json.dumps({"assets_ids": sorted(add), "type": "market", "operation": "subscribe"}))
                        if rem:
                            await ws.send(json.dumps({"assets_ids": sorted(rem), "type": "market", "operation": "unsubscribe"}))
                            with _lock:
                                for a in rem:
                                    books.pop(a, None)
                        subscribed = set(want); stats["subscribed"] = len(subscribed)
                    if now - last_rx > 30 and subscribed:
                        stats["silent_reconnects"] = stats.get("silent_reconnects", 0) + 1
                        break
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2)
                    except asyncio.TimeoutError:
                        continue
                    rx = time.time(); last_rx = rx; stats["msgs"] += 1; stats["last_msg"] = rx
                    if not isinstance(raw, str) or not raw or raw[0] not in "[{":
                        continue
                    try:
                        msgs = json.loads(raw)
                    except ValueError:
                        continue
                    if isinstance(msgs, dict):
                        msgs = [msgs]
                    hour = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")
                    if hour != out_hour:
                        if out:
                            out.close(); compress(out_hour)
                        out = open(f"{D}/{hour}.jsonl", "a"); out_hour = hour
                    for m in msgs:
                        if not isinstance(m, dict):
                            continue
                        rec = _apply(m, rx)
                        if rec:
                            rec["rx"] = round(rx, 4)
                            out.write(json.dumps(rec, separators=(",", ":")) + "\n")
                    out.flush()
        except Exception as e:  # noqa: BLE001
            stats["errors"] += 1; stats["last_error"] = str(e)[:160]
            await asyncio.sleep(3)
    if out:
        out.close(); compress(out_hour)


def start(active):
    """active: callable returning the list of asset ids to follow right now"""
    compress()
    stop = threading.Event()

    def runner():
        asyncio.run(_run(stop, active))
    threading.Thread(target=runner, daemon=True).start()
    return stop


if __name__ == "__main__":
    # standalone probe: follow the current BTC and ETH 5-minute windows for RUN_MIN minutes
    import requests
    S = requests.Session()
    def active():
        now = int(time.time()); toks = []
        for a in ("btc", "eth"):
            for st in (now // 300 * 300, now // 300 * 300 + 300):
                try:
                    ev = S.get("https://gamma-api.polymarket.com/events", params={"slug": f"{a}-updown-5m-{st}"}, timeout=10).json()
                    toks += json.loads(ev[0]["markets"][0]["clobTokenIds"])
                except Exception:  # noqa: BLE001
                    pass
        return toks
    cache = {"t": 0, "v": []}
    def cached():
        if time.time() - cache["t"] > 20:
            cache["v"] = active(); cache["t"] = time.time()
        return cache["v"]
    s = start(cached)
    end = time.time() + float(os.environ.get("RUN_MIN", "3")) * 60
    while time.time() < end:
        time.sleep(15)
        print(json.dumps(stats), {a[:8]: best(a) for a in list(books)[:4]}, flush=True)
    s.set(); time.sleep(1)
