from __future__ import annotations

import asyncio
import io
import json
import time
from typing import Any, Dict, List, Tuple

import httpx
from reportlab.lib.pagesizes import letter  # type: ignore
from reportlab.pdfgen import canvas  # type: ignore

API_BASE = "http://127.0.0.1:8000"
AUTO_PAY = True
PAUSE_SECONDS = 0.35


def print_timeline(events: List[Tuple[str, str]]):
    print("\n" + "=" * 64)
    print("Flow Timeline")
    print("-" * 64)
    for i, (label, detail) in enumerate(events, start=1):
        print(f"[{i}] {label:<26} {detail}")
    print("=" * 64 + "\n")


async def call_with_mock_x402(method: str, path: str, **kwargs) -> Any:
    url = API_BASE + path
    events: List[Tuple[str, str]] = []
    headers = kwargs.pop("headers", {})
    async with httpx.AsyncClient() as client:
        # First attempt (unpaid)
        events.append((f"Sent {method}", path))
        resp = await client.request(method, url, headers=headers, **kwargs)
        if resp.status_code == 402:
            body = resp.json()
            price = resp.headers.get("X-X402-Price") or body.get("price")
            pay_to = resp.headers.get("X-X402-PayTo") or body.get("pay_to")
            path_hdr = resp.headers.get("X-X402-Path") or body.get("path")
            events.append(("Received 402", f"price=${price} pay_to={pay_to} path={path_hdr}"))
            print_timeline(events)
            print("PAYMENT REQUIRED")
            print(json.dumps(body, indent=2))
            if not AUTO_PAY:
                input("Press Enter to simulate payment + retry...")
            else:
                time.sleep(PAUSE_SECONDS)
            events.append(("Retrying", "Adding X-X402-Mock-Paid:true"))
            headers = dict(headers)
            headers["X-X402-Mock-Paid"] = "true"
            resp = await client.request(method, url, headers=headers, **kwargs)

        # Success or other code
        settled = resp.headers.get("X-X402-Mock-Settled") == "true"
        events.append((f"Received {resp.status_code}", f"settled={settled}"))
        print_timeline(events)
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type:
            return resp.json()
        return resp.text


def build_sample_csv() -> bytes:
    import pandas as pd  # type: ignore

    data = [
        {"name": " Alice ", "age": "30", "city": "NYC", "email": "alice@example.com", "phone": "555-111-2222"},
        {"name": "Bob", "age": "-5", "city": "nyc", "email": "bob@example.com", "phone": "555-333-0000"},
        {"name": "Cara", "age": "28", "city": "SF", "email": "bad@", "phone": "invalid"},
        {"name": "Bob", "age": "35", "city": "NYC", "email": "bob@example.com", "phone": "555-333-0000"},
        {"name": "Dana", "age": "notanumber", "city": "LA", "email": "dana@example.com", "phone": "555-999-8888"},
    ]
    df = pd.DataFrame(data)
    return df.to_csv(index=False).encode("utf-8")


def build_sample_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 720, "x402 Mock PDF Demo")
    c.drawString(72, 700, "This is a tiny PDF generated on the fly for testing.")
    c.drawString(72, 680, "Page 1 content.")
    c.showPage()
    c.drawString(72, 720, "Second page")
    c.drawString(72, 700, "More sample text for extraction.")
    c.save()
    return buf.getvalue()


async def demo():
    # /summarize/logs
    print("\n=== /summarize/logs ===")
    res = await call_with_mock_x402(
        "POST",
        "/summarize/logs",
        content="ERROR db timeout\nERROR db timeout\nWARN cache miss",
        headers={"Content-Type": "text/plain"},
    )
    print(json.dumps(res, indent=2)[:500])

    # /clean/dataframe JSON
    print("\n=== /clean/dataframe (JSON) ===")
    payload = {
        "data": [
            {"name": " Alice ", "age": "30", "city": "nyc", "joined": "2024-01-01"},
            {"name": "Bob", "age": "thirty", "city": "NYC", "joined": "2024/02/01"},
            {"name": "Alice", "age": "30", "city": "nyc", "joined": "2024-01-01"},
            {"name": "Cara", "age": "-5", "city": "nyc", "joined": "not-a-date"},
            {"name": "Dana", "age": "notanumber", "city": "SF", "joined": ""},
        ],
        "rules": {
            "normalize_columns": True,
            "trim_strings": True,
            "deduplicate": True,
            "coerce_types": {"age": "int"},
            "parse_dates": ["joined"],
        },
    }
    res = await call_with_mock_x402("POST", "/clean/dataframe", json=payload)
    print(json.dumps(res, indent=2)[:500])

    # /clean/dataframe CSV
    print("\n=== /clean/dataframe (CSV) ===")
    csv_bytes = build_sample_csv()
    form = {
        "file": ("sample.csv", csv_bytes, "text/csv"),
        "rules": (None, json.dumps({"remove_negative_rows": True, "normalize_columns": True})),
        "include_csv": (None, "true"),
    }
    async with httpx.AsyncClient() as client:
        res = await call_with_mock_x402(
            "POST",
            "/clean/dataframe",
            files=form,
        )
    print(json.dumps(res, indent=2)[:500])

    # /validate/csv
    print("\n=== /validate/csv ===")
    config = {
        "no_empty_cells": True,
        "type_rules": {"age": {"type": "int", "min": 0}},
        "regex_rules": {"email": {"pattern": r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", "required": False}},
        "include_csv": True,
    }
    files = {
        "file": ("sample.csv", csv_bytes, "text/csv"),
        "config": (None, json.dumps(config)),
    }
    res = await call_with_mock_x402("POST", "/validate/csv", files=files)
    print(json.dumps(res, indent=2)[:500])

    # /extract/pdf
    print("\n=== /extract/pdf ===")
    pdf_bytes = build_sample_pdf()
    files = {"file": ("demo.pdf", pdf_bytes, "application/pdf"), "mode": (None, "text")}
    res = await call_with_mock_x402("POST", "/extract/pdf", files=files)
    if isinstance(res, dict):
        preview = {k: (v[:120] + "..." if isinstance(v, str) and len(v) > 120 else v) for k, v in res.items()}
        print(json.dumps(preview, indent=2))
    else:
        print(str(res)[:200])


if __name__ == "__main__":
    asyncio.run(demo())
