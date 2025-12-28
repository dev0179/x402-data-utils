# x402 Data Utilities

Paid, agent-friendly data utility endpoints protected by x402.

## Endpoints (paid)
- POST `/validate/csv`  ($0.01)
- POST `/clean/dataframe` ($0.02) - accepts JSON rows OR CSV upload
- POST `/extract/pdf` ($0.05)
- POST `/summarize/logs` ($0.03)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export PAY_TO_ADDRESS=0xYourEvmAddressHere
uvicorn main:app --reload
```

Open docs:
- http://127.0.0.1:8000/docs

## Client demo (auto-pay)
Edit `client_demo.py` and put your private key in `YOUR_PRIVATE_KEY` (never commit it).

```bash
python client_demo.py
```

## Notes
For production, add rate limiting, request size limits, and a secure settlement configuration.

## Mock + UI Demo (no real payments)
Run a local mock gate and UI to show 402 → pay → 200 without money or blockchain.

```bash
export MOCK_X402=1
export PAY_TO_ADDRESS=0x1111111111111111111111111111111111111111
uvicorn main:app --reload
# Open in browser:
http://127.0.0.1:8000
```

What to click to prove it works:
- Leave “Include Mock Paid Header” unchecked. Click “Send” in `/summarize/logs` → see HTTP 402, headers `X-X402-Price/PayTo/Path`, and 402 log `[x402-mock] 402 issued ...`.
- Turn the toggle on. Click “Send” again → see HTTP 200, header `X-X402-Mock-Settled: true`, and log `[x402-mock] payment accepted ...`.
- Repeat with `/clean/dataframe (JSON)` to show the same 402 → 200 behavior while returning cleaned data.

## Mock x402 handshake demo (no money)
Run a terminal demo that automatically does unpaid → 402 → paid retry → 200 for all endpoints.

```bash
export MOCK_X402=1
export PAY_TO_ADDRESS=0x1111111111111111111111111111111111111111
python -m uvicorn main:app --reload
python mock_handshake_demo.py
```

What it proves:
- First call gets HTTP 402 with `X-X402-Price/PayTo/Path` and JSON payment instructions.
- Client auto-retries with `X-X402-Mock-Paid:true`.
- Second call returns 200 with `X-X402-Mock-Settled:true`.
- Timeline prints each step so it’s clear in a screen recording.

## CSV validation (advanced rules)
`POST /validate/csv` now supports a full rule config. Send multipart with `file=<csv>` and `config=<json string>` (UI builds this for you). Default behavior stays compatible; add rules as needed.

Example config:
```json
{
  "required_columns": ["email", "phone"],
  "no_empty_headers": true,
  "no_empty_rows": true,
  "no_empty_cells": false,
  "strip_whitespace": true,
  "max_rows": 50000,
  "max_cols": 200,
  "type_rules": {
    "price": {"type": "float", "min": 0},
    "quantity": {"type": "int", "min": 0}
  },
  "regex_rules": {
    "phone": {"pattern": "^\\+?[0-9()\\-\\s]{7,}$", "required": false},
    "email": {"pattern": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", "required": false}
  },
  "enum_rules": {
    "state": {"allowed": ["CA", "IL", "TX"], "required": false}
  },
  "date_rules": {
    "date": {"format": "auto", "required": false}
  },
  "unique_rules": [
    {"columns": ["date", "product_id"], "case_insensitive": true}
  ],
  "range_rules": {
    "age": {"min": 0, "max": 120}
  },
  "sample_errors_limit": 200
}
```

UI helps build this: toggle strip/empties, choose phone/email regex columns, add non-negative numeric columns, unique constraints, and advanced type/regex JSON. Results panel shows status, counts, top 20 errors, and a “Download full report JSON” button.
