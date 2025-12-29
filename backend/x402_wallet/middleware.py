from __future__ import annotations

from typing import Dict

from fastapi import Request
from fastapi.responses import JSONResponse

from .invoice import issue_invoice
from .store import InvoiceStore
from .verify import parse_proof_header, verify_proof


def install_wallet_middleware(app, store: InvoiceStore, pay_to_address: str, route_prices: Dict[str, str], invoice_ttl: int) -> None:
    @app.middleware("http")
    async def _wallet_gate(request: Request, call_next):
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        price = route_prices.get(request.url.path)
        if price is None:
            return await call_next(request)

        proof_header = request.headers.get("x-x402-proof")
        base_cors = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }

        if not proof_header:
            invoice = issue_invoice(path=request.url.path, price=price, pay_to=pay_to_address, ttl_seconds=invoice_ttl, store=store)
            headers = {
                "X-X402-Mode": "wallet",
                "X-X402-Price": price,
                "X-X402-PayTo": pay_to_address,
                "X-X402-Path": request.url.path,
                "X-X402-InvoiceId": invoice["invoice_id"],
                **base_cors,
            }
            print(f"[x402-wallet] 402 issued invoice_id={invoice['invoice_id']} path={request.url.path} price={price}")
            return JSONResponse(
                {
                    "error": "payment required",
                    "mode": "wallet",
                    "invoice": invoice,
                    "how_to_pay": "Sign the canonical message and retry with X-X402-Proof",
                },
                status_code=402,
                headers=headers,
            )

        proof = parse_proof_header(proof_header)
        ok, reason, payer, invoice_id, receipt_id = verify_proof(proof, store)
        if not ok:
            headers = {
                "X-X402-Mode": "wallet",
                "X-X402-Price": price,
                "X-X402-PayTo": pay_to_address,
                "X-X402-Path": request.url.path,
                "X-X402-InvoiceId": invoice_id,
                **base_cors,
            }
            return JSONResponse(
                {"error": "payment required", "mode": "wallet", "reason": reason, "invoice_id": invoice_id},
                status_code=402,
                headers=headers,
            )

        print(f"[x402-wallet] verified payer={payer} invoice_id={invoice_id} receipt={receipt_id}")
        response = await call_next(request)
        response.headers["X-X402-Receipt"] = receipt_id
        response.headers["X-X402-Payer"] = payer
        response.headers["X-X402-Price"] = price
        response.headers["X-X402-Path"] = request.url.path
        response.headers["X-X402-PayTo"] = pay_to_address
        response.headers["X-X402-Mode"] = "wallet"
        return response
