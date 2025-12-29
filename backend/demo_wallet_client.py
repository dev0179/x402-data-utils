from __future__ import annotations

import base64
import json
import asyncio
from typing import Any, Dict, List, Tuple

import httpx
from eth_account import Account  # type: ignore
from eth_account.messages import encode_defunct  # type: ignore

from .x402_wallet.invoice import canonical_message

API_BASE = "http://127.0.0.1:8000"


def timeline_print(events: List[Tuple[str, str]]):
    print("\n=== Handshake Timeline ===")
    for i, (label, detail) in enumerate(events, 1):
        print(f"[{i}] {label:<18} {detail}")
    print("==========================\n")


async def call_with_wallet(path: str, body: Dict[str, Any], privkey_hex: str, addr: str):
    events: List[Tuple[str, str]] = []
    async with httpx.AsyncClient() as client:
        events.append(("Sent POST", path))
        res = await client.post(API_BASE + path, json=body)
        if res.status_code != 402:
            print(f"Expected 402, got {res.status_code}: {res.text}")
            return

        data = res.json()
        invoice = data.get("invoice", {})
        events.append(("Received 402", f"id={invoice.get('invoice_id')} price={invoice.get('price')} pay_to={invoice.get('pay_to')}"))
        timeline_print(events)

        msg = canonical_message(invoice)
        signed = Account.sign_message(encode_defunct(text=msg), private_key=privkey_hex)
        proof = {
            "invoice": invoice,
            "payer": addr,
            "signature": signed.signature.hex(),
        }
        proof_b64 = base64.b64encode(json.dumps(proof).encode("utf-8")).decode("utf-8")
        events.append(("Signed invoice", f"payer={addr}"))
        events.append(("Retrying", "with X-X402-Proof"))

        res2 = await client.post(API_BASE + path, json=body, headers={"X-X402-Proof": proof_b64})
        events.append(("Received", f"{res2.status_code} receipt={res2.headers.get('x-x402-receipt','-')}"))
        timeline_print(events)
        print("Response body (truncated):")
        try:
            print(json.dumps(res2.json(), indent=2)[:400])
        except Exception:
            print(str(res2.text)[:400])

        # replay attempt
        events.append(("Replay", "reusing proof"))
        res3 = await client.post(API_BASE + path, json=body, headers={"X-X402-Proof": proof_b64})
        events.append(("Replay result", f"{res3.status_code} reason={res3.json().get('reason') if res3.headers.get('content-type','').startswith('application/json') else res3.text}"))
        timeline_print(events)


async def main():
    acct = Account.create()
    print("Ephemeral wallet:", acct.address)

    # Example: summarize logs
    payload = {"text": "ERROR db timeout\nERROR db timeout\nWARN cache miss"}
    await call_with_wallet("/summarize/logs", payload, acct.key.hex(), acct.address)


if __name__ == "__main__":
    asyncio.run(main())
