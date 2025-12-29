# x402 Data Utilities (wallet-signed, no chain)

End-to-end data utility service (FastAPI backend + Next.js frontend) gated by a local x402-style invoice/signature flow. No blockchain calls or real payments.

## Endpoints & Prices
- `POST /validate/csv` ($0.01)
- `POST /clean/dataframe` ($0.05)
- `POST /extract/pdf` ($0.05) — now text-only (tables removed)
- `POST /summarize/logs` ($0.02)

## Wallet Flow (local-only)
- First call to a protected route returns HTTP 402 with an invoice.
- Canonical message: `x402-local-wallet|invoice_id=<id>|path=<path>|price=<price>|pay_to=<pay_to>|nonce=<nonce>|expires_at=<expires_at>`
- Client signs with a local EVM wallet (eth_account) and retries with `X-X402-Proof` (base64 JSON: `{invoice, payer, signature}`).
- Success returns 200 + headers `X-X402-Receipt`, `X-X402-Payer` (plus price/path/pay_to).

## Env Vars
- `PAY_TO_ADDRESS` (required)
- `INVOICE_TTL_SECONDS` (optional, default 300)
- `REDIS_URL` (optional; if absent, in-memory store is used)
- `NEXT_PUBLIC_API_BASE` (frontend) — API base URL (e.g., `http://localhost:8000` or your Render URL)

## Backend (FastAPI, in `backend/`)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
export PAY_TO_ADDRESS=0x1111111111111111111111111111111111111111
uvicorn backend.main:app --reload
# Docs: http://127.0.0.1:8000/docs
```

Render deploy: use `Procfile` (`web: uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}`) and set `PAY_TO_ADDRESS` (and `REDIS_URL` if desired).

## Frontend (Next.js in `website/`)
```bash
cd website
npm install
export NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000  # or your Render backend URL
npm run dev
```
Vercel deploy: set project root to `website/`, build `npm run build`, and set `NEXT_PUBLIC_API_BASE` to your backend URL. Base path/asset prefix are `/x402` for path-based hosting.

## Live Preview
Current frontend + wallet-signed flow is hosted at https://www.devank.cv/x402 (path-based, mock local wallet signing).

## Demo Script (terminal)
```bash
python backend/demo_wallet_client.py
```
Shows 402 invoice -> signed proof -> 200 receipt -> replay rejected.

## Testing
```bash
pytest
```
(Requires `PAY_TO_ADDRESS` set; tests use in-memory store.)

## Invoice Example (402 response body)
```json
{
  "invoice_id": "<uuid>",
  "path": "/summarize/logs",
  "price": "0.03",
  "pay_to": "<pay_to_address>",
  "nonce": "<random>",
  "issued_at": "<iso>",
  "expires_at": "<iso>",
  "asset": "local-usdc",
  "chain": "local",
  "domain": "x402-local-wallet"
}
```
