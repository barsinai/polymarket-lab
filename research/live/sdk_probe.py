"""Print the public surface of the official SDK (polymarket-client) so the broker can be written
against the real method names. No keys, no network beyond pip."""
import importlib, inspect, pkgutil, sys
try:
    import polymarket
except ImportError as e:
    print("import failed:", e); sys.exit(0)
print("polymarket", getattr(polymarket, "__version__", "?"), polymarket.__file__)
for mi in pkgutil.walk_packages(polymarket.__path__, "polymarket."):
    print("MODULE", mi.name)
names = [n for n in dir(polymarket) if not n.startswith("_")]
print("TOP-LEVEL:", names)
for cname in ("SecureClient", "AsyncSecureClient", "PublicClient", "RelayerApiKey", "BuilderApiKey"):
    c = getattr(polymarket, cname, None)
    if c is None:
        continue
    print(f"\n=== {cname}")
    try:
        print(inspect.signature(c.create) if hasattr(c, "create") else inspect.signature(c))
    except (TypeError, ValueError) as e:
        print("sig?", e)
    for n, m in inspect.getmembers(c):
        if n.startswith("_") or not callable(m):
            continue
        try:
            sig = str(inspect.signature(m))
        except (TypeError, ValueError):
            sig = "(?)"
        doc = (inspect.getdoc(m) or "").split("\n")[0][:110]
        print(f"  {n}{sig[:160]}  # {doc}")
# order-related types
for mod in ("polymarket.clob", "polymarket.clob.types", "polymarket.types", "polymarket.models", "polymarket.clob.models"):
    try:
        m = importlib.import_module(mod)
    except ImportError:
        continue
    print(f"\n=== {mod}:", [n for n in dir(m) if not n.startswith("_")][:200])
    for n in dir(m):
        o = getattr(m, n)
        if inspect.isclass(o) and any(k in n.lower() for k in ("order", "side", "tick", "balance", "trade")):
            try:
                print(f"  class {n}{inspect.signature(o)}"[:300])
            except (TypeError, ValueError):
                print(f"  class {n}")
