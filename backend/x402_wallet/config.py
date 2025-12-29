import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class WalletConfig:
    pay_to_address: str
    invoice_ttl_seconds: int
    redis_url: Optional[str]
    route_prices: Dict[str, str]


def load_config(route_prices: Dict[str, str]) -> WalletConfig:
    pay_to = os.getenv("PAY_TO_ADDRESS")
    if not pay_to:
        raise RuntimeError("Missing PAY_TO_ADDRESS env var. Set it to the pay-to address shown on invoices.")

    ttl_env = os.getenv("INVOICE_TTL_SECONDS")
    try:
        ttl = int(ttl_env) if ttl_env else 300
    except ValueError:
        ttl = 300

    redis_url = os.getenv("REDIS_URL")
    env = os.getenv("APP_ENV", "").lower()
    if not redis_url and env in {"prod", "production"}:
        print("[x402-wallet] Warning: running without REDIS_URL in production; replay protection is in-memory only.")

    return WalletConfig(pay_to_address=pay_to, invoice_ttl_seconds=ttl, redis_url=redis_url, route_prices=route_prices)
