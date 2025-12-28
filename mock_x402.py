from __future__ import annotations

from typing import Dict

from fastapi import Request
from fastapi.responses import JSONResponse


def install_mock_x402(app, pay_to_address: str, route_prices: Dict[str, str]) -> None:
    """
    Mock x402 middleware installer.
    - If request path is gated and lacks header X-X402-Mock-Paid:true -> return 402 with pricing headers.
    - If header is present -> allow through and tag response with X-X402-Mock-Settled:true.
    """

    @app.middleware("http")
    async def _mock_x402(request: Request, call_next):
        # Let preflight requests pass through without gating
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        price = route_prices.get(request.url.path)
        if price is None:
            return await call_next(request)

        paid_header = request.headers.get("x-x402-mock-paid", "").lower()
        if paid_header == "true":
            print(f"[x402-mock] payment accepted path={request.url.path} price={price}")
            response = await call_next(request)
            response.headers["X-X402-Price"] = price
            response.headers["X-X402-PayTo"] = pay_to_address
            response.headers["X-X402-Path"] = request.url.path
            response.headers["X-X402-Mock-Settled"] = "true"
            response.headers["X-X402-Mock"] = "true"
            return response

        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
        headers = {
            "X-X402-Price": price,
            "X-X402-PayTo": pay_to_address,
            "X-X402-Path": request.url.path,
            "X-X402-Mock": "true",
        }
        headers.update(cors_headers)
        print(f"[x402-mock] 402 issued path={request.url.path} price={price}")
        return JSONResponse(
            {
                "error": "payment required",
                "mock": True,
                "path": request.url.path,
                "price": price,
                "pay_to": pay_to_address,
                "how_to_pay": "Retry with header X-X402-Mock-Paid: true",
            },
            status_code=402,
            headers=headers,
        )
