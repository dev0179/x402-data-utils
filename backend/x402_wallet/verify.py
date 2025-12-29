from __future__ import annotations

import base64
import json
from typing import Any, Dict, Tuple

from eth_account import Account  # type: ignore
from eth_account.messages import encode_defunct  # type: ignore

from .invoice import canonical_message
from .store import InvoiceStore


def parse_proof_header(raw: str) -> Dict[str, Any]:
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        try:
            return json.loads(raw)
        except Exception:
            return {}


def verify_proof(proof: Dict[str, Any], store: InvoiceStore) -> Tuple[bool, str, str, str, str]:
    """
    Returns (ok, reason_or_receipt, payer, invoice_id, receipt_id_or_empty)
    """
    try:
        invoice = proof["invoice"]
        payer = str(proof["payer"])
        signature = proof["signature"]
    except Exception:
        return False, "invalid proof format", "", "", ""

    invoice_id = invoice.get("invoice_id", "")
    record = store.get_invoice(invoice_id)
    if not record:
        return False, "invoice not found or expired", payer, invoice_id, ""

    if invoice != record["invoice"]:
        return False, "invoice mismatch", payer, invoice_id, ""

    # verify signature
    msg = canonical_message(invoice)
    try:
        recovered = Account.recover_message(encode_defunct(text=msg), signature=signature)
    except Exception:
        return False, "signature recover failed", payer, invoice_id, ""

    if recovered.lower() != payer.lower():
        return False, "payer mismatch", recovered, invoice_id, ""

    ok, receipt_or_reason = store.mark_redeemed(invoice_id, recovered)
    if not ok:
        return False, receipt_or_reason, recovered, invoice_id, ""

    return True, "ok", recovered, invoice_id, receipt_or_reason
