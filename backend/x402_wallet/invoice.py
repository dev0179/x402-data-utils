from __future__ import annotations

import time
import uuid
from typing import Any, Dict

from .store import InvoiceStore

DEFAULT_ASSET = "local-usdc"
DEFAULT_CHAIN = "local"
DEFAULT_DOMAIN = "x402-local-wallet"


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def issue_invoice(path: str, price: str, pay_to: str, ttl_seconds: int, store: InvoiceStore) -> Dict[str, Any]:
    issued_at_ts = time.time()
    expires_at_ts = issued_at_ts + ttl_seconds
    invoice = {
        "invoice_id": str(uuid.uuid4()),
        "path": path,
        "price": price,
        "pay_to": pay_to,
        "nonce": str(uuid.uuid4()),
        "issued_at": _iso(issued_at_ts),
        "expires_at": _iso(expires_at_ts),
        "asset": DEFAULT_ASSET,
        "chain": DEFAULT_CHAIN,
        "domain": DEFAULT_DOMAIN,
    }
    store.save_invoice(invoice, expires_at_ts)
    return invoice


def canonical_message(invoice: Dict[str, Any]) -> str:
    return (
        f"{DEFAULT_DOMAIN}|"
        f"invoice_id={invoice['invoice_id']}|"
        f"path={invoice['path']}|"
        f"price={invoice['price']}|"
        f"pay_to={invoice['pay_to']}|"
        f"nonce={invoice['nonce']}|"
        f"expires_at={invoice['expires_at']}"
    )
