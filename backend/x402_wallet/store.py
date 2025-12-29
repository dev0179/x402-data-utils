from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any, Dict, Optional, Tuple

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis optional
    redis = None


class InvoiceStore:
    def save_invoice(self, invoice: Dict[str, Any], expires_at_ts: float) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:  # pragma: no cover - interface
        raise NotImplementedError

    def mark_redeemed(self, invoice_id: str, payer: str) -> Tuple[bool, str]:
        """Return (ok, receipt_id_or_reason)."""
        raise NotImplementedError


class InMemoryStore(InvoiceStore):
    def __init__(self):
        self._invoices: Dict[str, Dict[str, Any]] = {}
        self._receipts: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        expired = [iid for iid, rec in self._invoices.items() if now > rec["expires_at"]]
        for iid in expired:
            self._invoices.pop(iid, None)

    def save_invoice(self, invoice: Dict[str, Any], expires_at_ts: float) -> None:
        with self._lock:
            self._prune(time.time())
            self._invoices[invoice["invoice_id"]] = {
                "invoice": invoice,
                "expires_at": expires_at_ts,
                "redeemed": False,
            }

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            now = time.time()
            self._prune(now)
            rec = self._invoices.get(invoice_id)
            if not rec:
                return None
            if now > rec["expires_at"]:
                return None
            return rec

    def mark_redeemed(self, invoice_id: str, payer: str) -> Tuple[bool, str]:
        with self._lock:
            rec = self._invoices.get(invoice_id)
            if not rec:
                return False, "invoice not found"
            if time.time() > rec["expires_at"]:
                return False, "invoice expired"
            if rec.get("redeemed"):
                return False, "invoice already redeemed"
            rec["redeemed"] = True
            receipt_id = str(uuid.uuid4())
            self._receipts[receipt_id] = {"invoice_id": invoice_id, "payer": payer, "ts": time.time()}
            return True, receipt_id


class RedisStore(InvoiceStore):
    def __init__(self, url: str):
        if redis is None:  # pragma: no cover - env without redis
            raise RuntimeError("redis-py not installed")
        self._r = redis.Redis.from_url(url)

    def save_invoice(self, invoice: Dict[str, Any], expires_at_ts: float) -> None:
        ttl = max(1, int(expires_at_ts - time.time()))
        key = f"invoice:{invoice['invoice_id']}"
        payload = json.dumps({"invoice": invoice, "expires_at": expires_at_ts, "redeemed": False})
        self._r.set(key, payload, ex=ttl)

    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        raw = self._r.get(f"invoice:{invoice_id}")
        if not raw:
            return None
        try:
            rec = json.loads(raw)
        except Exception:
            return None
        if time.time() > rec.get("expires_at", 0):
            return None
        return rec

    def mark_redeemed(self, invoice_id: str, payer: str) -> Tuple[bool, str]:
        key = f"invoice:{invoice_id}"
        pipe = self._r.pipeline()
        while True:
            try:
                pipe.watch(key)
                raw = pipe.get(key)
                if not raw:
                    pipe.unwatch()
                    return False, "invoice not found"
                rec = json.loads(raw)
                if time.time() > rec.get("expires_at", 0):
                    pipe.unwatch()
                    return False, "invoice expired"
                if rec.get("redeemed"):
                    pipe.unwatch()
                    return False, "invoice already redeemed"
                rec["redeemed"] = True
                receipt_id = str(uuid.uuid4())
                rec["receipt_id"] = receipt_id
                ttl = max(1, int(rec.get("expires_at", time.time()) - time.time()))
                pipe.multi()
                pipe.set(key, json.dumps(rec), ex=ttl)
                pipe.set(f"receipt:{receipt_id}", json.dumps({"invoice_id": invoice_id, "payer": payer, "ts": time.time()}), ex=ttl)
                pipe.execute()
                return True, receipt_id
            except redis.WatchError:  # type: ignore
                continue
            finally:
                pipe.reset()
