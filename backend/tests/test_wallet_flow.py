import os
import base64
import json
import time

import pytest
from fastapi.testclient import TestClient
from eth_account import Account  # type: ignore
from eth_account.messages import encode_defunct  # type: ignore

os.environ["PAY_TO_ADDRESS"] = "0x1111111111111111111111111111111111111111"

from backend import main  # type: ignore  # noqa: E402
from backend.x402_wallet.invoice import canonical_message


client = TestClient(main.app)


def _sign_invoice(inv, acct):
    msg = canonical_message(inv)
    signed = Account.sign_message(encode_defunct(text=msg), private_key=acct.key)
    proof = {"invoice": inv, "payer": acct.address, "signature": signed.signature.hex()}
    proof_b64 = base64.b64encode(json.dumps(proof).encode()).decode()
    return proof_b64


def _get_invoice():
    res = client.post("/summarize/logs", data="ERROR db timeout\n")
    assert res.status_code == 402
    return res.json()["invoice"]


def test_invoice_issued():
    inv = _get_invoice()
    assert inv["invoice_id"]
    assert inv["price"] == "0.03"
    assert inv["path"] == "/summarize/logs"


def test_valid_proof_succeeds_and_sets_headers():
    inv = _get_invoice()
    acct = Account.create()
    proof_b64 = _sign_invoice(inv, acct)
    res = client.post("/summarize/logs", data="ERROR db timeout\n", headers={"X-X402-Proof": proof_b64})
    assert res.status_code == 200
    assert res.headers.get("x-x402-receipt")
    assert res.headers.get("x-x402-payer")


def test_replay_fails():
    inv = _get_invoice()
    acct = Account.create()
    proof_b64 = _sign_invoice(inv, acct)
    res1 = client.post("/summarize/logs", data="ERROR db timeout\n", headers={"X-X402-Proof": proof_b64})
    assert res1.status_code == 200
    res2 = client.post("/summarize/logs", data="ERROR db timeout\n", headers={"X-X402-Proof": proof_b64})
    assert res2.status_code == 402


def test_expired_invoice_fails(monkeypatch):
    inv = _get_invoice()
    acct = Account.create()

    # Fast-forward expiration
    monkeypatch.setattr(main, "settings", main.settings)
    time.sleep(0.01)
    # manually adjust stored invoice expiration when using in-memory store
    if hasattr(main.store, "_invoices"):
        rec = main.store._invoices.get(inv["invoice_id"])
        if rec:
            rec["expires_at"] = time.time() - 1

    proof_b64 = _sign_invoice(inv, acct)
    res = client.post("/summarize/logs", data="ERROR db timeout\n", headers={"X-X402-Proof": proof_b64})
    assert res.status_code == 402
