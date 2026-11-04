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

# ---- full detail for the methods the broker needs
print("\n\n######## DETAIL")
SC = getattr(polymarket, "SecureClient", None)
if SC:
    for n in ("create", "place_limit_order", "create_limit_order", "post_order", "post_orders", "cancel_order", "cancel_orders", "cancel_all",
              "list_open_orders", "get_balance_allowance", "update_balance_allowance", "setup_trading_approvals", "get_trading_approvals_state",
              "list_account_trades", "list_user_earnings_for_day", "get_total_earnings_for_user_for_day", "get_current_rebates", "list_positions",
              "merge_positions", "redeem_positions", "get_order", "get_orders_scoring"):
        m = getattr(SC, n, None)
        if m is None:
            print("MISSING", n); continue
        try:
            print(f"\n--- {n}{inspect.signature(m)}")
        except (TypeError, ValueError):
            print(f"\n--- {n} (no signature)")
        print(inspect.getdoc(m) or "")
    for n in ("place_limit_order",):
        try:
            print("\n--- SOURCE", n); print(inspect.getsource(getattr(SC, n))[:3000])
        except (OSError, TypeError) as e:
            print("source?", e)
for mod in ("polymarket._internal.actions.orders.limit", "polymarket._internal.actions.orders.post", "polymarket._internal.actions.orders.types"):
    try:
        m = importlib.import_module(mod); src = inspect.getsource(m)
        print(f"\n--- SOURCE {mod} ({len(src)} chars)\n" + src[:6000])
    except Exception as e:  # noqa: BLE001
        print(mod, "?", e)
for mod, names in (("polymarket.models.clob.account", None), ("polymarket.models.clob.orders", None), ("polymarket.models.clob.order_response", None),
                   ("polymarket.models.clob.balance_allowance", None), ("polymarket.models.clob.rewards", None), ("polymarket.models.trading", None)):
    try:
        m = importlib.import_module(mod)
    except ImportError as e:
        print(mod, "?", e); continue
    for n in dir(m):
        o = getattr(m, n)
        if inspect.isclass(o) and o.__module__ == mod:
            fields = getattr(o, "model_fields", None) or getattr(o, "__dataclass_fields__", None) or getattr(o, "__annotations__", {})
            print(f"{mod}.{n}: {list(fields)[:40]}")
