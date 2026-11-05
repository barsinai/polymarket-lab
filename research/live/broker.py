"""Thin wrapper around the official SDK (polymarket-client >= 0.16) for the pilot.

Credentials come ONLY from the environment (GitHub Actions secrets):
  POLYMARKET_PRIVATE_KEY, POLYMARKET_WALLET_ADDRESS, POLYMARKET_RELAYER_API_KEY, POLYMARKET_SIGNER_ADDRESS
Nothing here prints or stores them. `send=False` (dry run) signs orders to validate them but never posts,
never cancels and never submits transactions.
"""
import os, time
from datetime import datetime, timezone
from decimal import Decimal


def _dec(x):
    try:
        return Decimal(str(x))
    except Exception:  # noqa: BLE001
        return Decimal(0)


def _usd(x):
    """balances come back in base units (6 decimals) or dollars depending on the endpoint: normalise"""
    d = _dec(x)
    return float(d / Decimal(10 ** 6)) if d >= 100000 else float(d)


class Broker:
    def __init__(self, send=False):
        from polymarket import RelayerApiKey, SecureClient
        self.send = send
        key = os.environ["POLYMARKET_PRIVATE_KEY"]
        wallet = os.environ.get("POLYMARKET_WALLET_ADDRESS") or None
        rk, ra = os.environ.get("POLYMARKET_RELAYER_API_KEY"), os.environ.get("POLYMARKET_SIGNER_ADDRESS")
        api_key = RelayerApiKey(key=rk, address=ra) if rk and ra else None
        self.client = SecureClient.create(private_key=key, wallet=wallet, api_key=api_key)
        self.wallet = str(getattr(self.client, "wallet", wallet))
        self.wallet_type = str(getattr(self.client, "wallet_type", "?"))

    # ---- account
    def balance(self):
        b = self.client.get_balance_allowance(asset_type="COLLATERAL")
        return {"balance_usd": _usd(getattr(b, "balance", 0)), "raw": str(getattr(b, "balance", ""))[:40]}

    def approvals(self):
        s = self.client.get_trading_approvals_state()
        return {"fully_approved": bool(getattr(s, "is_fully_approved", False)), "missing": str(getattr(s, "missing", ""))[:300]}

    def ensure_approvals(self):
        """one-time: grant the standard trading approvals (gasless for Deposit Wallets). Only when sending."""
        st = self.approvals()
        if st["fully_approved"] or not self.send:
            return st
        h = self.client.setup_trading_approvals()
        try:
            h.wait()
        except Exception:  # noqa: BLE001
            pass
        return self.approvals()

    def positions(self):
        """cid -> {yes: signed shares (Yes positive, No negative), tokens: {token_id: shares}, value}"""
        out = {}
        self.sample_position = None
        for p in self.client.list_positions(status="OPEN").iter_items():
            if self.sample_position is None:
                self.sample_position = repr(p)[:500]
            cid = str(getattr(p, "condition_id", "") or "")
            size = float(getattr(p, "current_size", None) or getattr(p, "size", 0) or 0)
            outcome = str(getattr(p, "outcome", "") or "")
            idx = getattr(p, "outcome_index", None)
            tok = str(getattr(p, "asset_id", "") or "")
            is_yes = (idx == 0) if idx is not None else (outcome.lower() == "yes")
            o = out.setdefault(cid, {"yes": 0.0, "tokens": {}, "value": 0.0, "q": str(getattr(p, "title", "") or "")[:80]})
            o["yes"] += size if is_yes else -size
            o["tokens"][tok] = size
            o["value"] += float(getattr(p, "current_value", 0) or 0)
        return out

    # ---- orders
    def open_orders(self):
        """list of {id, token, side, price, remaining, cid}"""
        out = []
        for o in self.client.list_open_orders().iter_items():
            rem = float(getattr(o, "original_size", 0) or 0) - float(getattr(o, "size_matched", 0) or 0)
            ex = getattr(o, "expires_at", None)
            ex_ts = ex.timestamp() if isinstance(ex, datetime) else (float(ex) if ex else None)
            out.append({"id": str(o.id), "token": str(getattr(o, "asset_id", "")), "side": str(getattr(o, "side", "")).upper(),
                        "price": float(getattr(o, "price", 0) or 0), "remaining": rem, "cid": str(getattr(o, "condition_id", "") or ""), "expires_at": ex_ts})
        return out

    def post(self, token, side, price, size, ttl_s=1500):
        """post-only limit order that expires on its own after ttl_s (default 25 min): if the bot dies,
        nothing stays resting. Dry run: sign only (validates tick/size/allowance paths)."""
        exp = int(time.time()) + int(ttl_s)
        if not self.send:
            self.client.create_limit_order(asset_id=token, price=str(price), size=str(size), side=side, post_only=True, expiration=exp)
            return {"ok": True, "dry": True}
        r = self.client.place_limit_order(asset_id=token, price=str(price), size=str(size), side=side, post_only=True, expiration=exp)
        if getattr(r, "ok", False):
            return {"ok": True, "order_id": str(getattr(r, "order_id", "")), "status": str(getattr(r, "status", ""))}
        return {"ok": False, "code": str(getattr(r, "code", "")), "message": str(getattr(r, "message", ""))[:200]}

    def cancel(self, order_ids):
        if not order_ids or not self.send:
            return {"dry": True, "n": len(order_ids)}
        r = self.client.cancel_orders(order_ids=list(order_ids))
        return {"canceled": len(getattr(r, "canceled", []) or []), "not_canceled": str(getattr(r, "not_canceled", ""))[:200]}

    def cancel_all(self):
        if not self.send:
            return {"dry": True}
        r = self.client.cancel_all()
        return {"canceled": len(getattr(r, "canceled", []) or [])}

    # ---- fills, rewards, housekeeping
    def trades_since(self, ts):
        out = []
        for t in self.client.list_account_trades().iter_items():
            m = getattr(t, "matched_at", None)
            mt = m.timestamp() if isinstance(m, datetime) else float(m or 0)
            if mt and mt < ts:
                break
            out.append({"id": str(t.id), "cid": str(getattr(t, "condition_id", "")), "token": str(getattr(t, "asset_id", "")), "side": str(getattr(t, "side", "")),
                        "trader_side": str(getattr(t, "trader_side", "")), "price": float(getattr(t, "price", 0) or 0), "size": float(getattr(t, "size", 0) or 0),
                        "outcome": str(getattr(t, "outcome", "")), "fee_bps": getattr(t, "fee_rate_bps", None), "status": str(getattr(t, "status", "")), "ts": mt})
        return out

    def earnings(self, date):
        """actual liquidity-reward earnings for a UTC day (YYYY-MM-DD): total and per market"""
        tot = sum(float(getattr(e, "earnings", 0) or 0) for e in self.client.get_total_earnings_for_user_for_day(date=date))
        per = {}
        for e in self.client.list_user_earnings_for_day(date=date).iter_items():
            per[str(getattr(e, "condition_id", ""))] = float(getattr(e, "earnings", 0) or 0)
        return {"date": date, "total": tot, "per_market": per}

    def rebates(self, date):
        return sum(float(getattr(r, "amount", 0) or getattr(r, "fee", 0) or 0) for r in self.client.get_current_rebates(date=date, maker_address=self.wallet))

    def merge_complementary(self, positions):
        """Yes+No of the same market held together = $1 locked: merge back to cash (gasless)."""
        done = []
        for cid, p in positions.items():
            sizes = sorted(p["tokens"].values())
            if len(sizes) == 2 and sizes[0] >= 1:
                if self.send:
                    try:
                        self.client.merge_positions(condition_id=cid, amount="max")
                    except Exception as e:  # noqa: BLE001
                        done.append({"cid": cid, "error": str(e)[:120]}); continue
                done.append({"cid": cid, "merged": sizes[0], "dry": not self.send})
        return done

    def redeem_resolved(self):
        done = []
        for p in self.client.list_positions(status="REDEEMABLE").iter_items():
            cid = str(getattr(p, "condition_id", "") or "")
            if self.send:
                try:
                    self.client.redeem_positions(condition_id=cid)
                except Exception as e:  # noqa: BLE001
                    done.append({"cid": cid, "error": str(e)[:120]}); continue
            done.append({"cid": cid, "redeemed": float(getattr(p, "current_size", None) or getattr(p, "size", 0) or 0), "dry": not self.send})
        return done
