from __future__ import annotations

import os
from io import BytesIO
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from cleaning import clean_df
from csv_validation import default_validation_config, validate_csv_full
from log_summarize import summarize_logs
from pdf_extract import extract_pdf
from x402_wallet.config import load_config
from x402_wallet.middleware import install_wallet_middleware
from x402_wallet.store import InMemoryStore, RedisStore

app = FastAPI(title="x402 Data Utilities (wallet-gated)", version="1.0.0")

# CORS for local frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

ROUTE_PRICES: Dict[str, str] = {
    "/validate/csv": "0.01",
    "/clean/dataframe": "0.05",
    "/extract/pdf": "0.05",
    "/summarize/logs": "0.02",
}

settings = load_config(ROUTE_PRICES)

if settings.redis_url:
    try:
        store = RedisStore(settings.redis_url)
        print("[x402-wallet] Using Redis store")
    except Exception as e:
        print(f"[x402-wallet] Failed to init Redis store ({e}), falling back to in-memory.")
        store = InMemoryStore()
else:
    store = InMemoryStore()
    print("[x402-wallet] Using in-memory invoice store")

install_wallet_middleware(
    app,
    store=store,
    pay_to_address=settings.pay_to_address,
    route_prices=settings.route_prices,
    invoice_ttl=settings.invoice_ttl_seconds,
)


@app.get("/health")
async def health():
    return {"ok": True}


async def read_upload_bytes(upload: UploadFile) -> bytes:
    b = await upload.read()
    if not b:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    return b


def df_to_json_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return df.replace({pd.NA: None, np.nan: None}).to_dict(orient="records")


def _merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = base.copy()
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            tmp = merged[k].copy()
            tmp.update(v)
            merged[k] = tmp
        else:
            merged[k] = v
    return merged


@app.post("/validate/csv")
async def validate_csv(
    request: Request,
    required_columns: Optional[str] = None,
    types: Optional[str] = None,
    config: Optional[str] = None,
    include_csv: Optional[bool] = None,
):
    import json

    def parse_json_field(raw_val: Optional[str], label: str):
        if raw_val is None:
            return None
        try:
            return json.loads(raw_val)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"{label} must be valid JSON: {e}")

    def build_config(form_cfg: Optional[str], query_cfg: Optional[str]) -> Dict[str, Any]:
        base_cfg = default_validation_config()
        req_cols_list = parse_json_field(required_columns, "required_columns")
        if req_cols_list:
            base_cfg["required_columns"] = req_cols_list
        type_map = parse_json_field(types, "types")
        if type_map:
            base_cfg["type_rules"] = {col: {"type": t} for col, t in type_map.items()}
        if include_csv is not None:
            base_cfg["include_csv"] = bool(include_csv)

        raw_cfg = form_cfg if form_cfg is not None else query_cfg
        if raw_cfg:
            cfg_obj = parse_json_field(raw_cfg, "config")
            if not isinstance(cfg_obj, dict):
                raise HTTPException(status_code=400, detail="config must be a JSON object")
            base_cfg = _merge_config(base_cfg, cfg_obj)
        return base_cfg

    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        form = await request.form()
        upload = form.get("file")
        if upload is None or not hasattr(upload, "filename"):
            raise HTTPException(status_code=400, detail="multipart form must include a CSV file field named 'file'.")
        upload_file: UploadFile = upload  # type: ignore
        if not upload_file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Please upload a .csv file")

        raw = await read_upload_bytes(upload_file)
        try:
            df = pd.read_csv(BytesIO(raw))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

        cfg_field = form.get("config") if "config" in form else None
        cfg_str = str(cfg_field) if cfg_field not in (None, "") else None
        cfg = build_config(form_cfg=cfg_str, query_cfg=config)
        return validate_csv_full(df, cfg)

    raise HTTPException(status_code=415, detail="Unsupported Content-Type. Use multipart/form-data.")


@app.post("/clean/dataframe")
async def clean_dataframe(request: Request):
    content_type = request.headers.get("content-type", "")
    rules_obj: Dict[str, Any] = {}
    include_csv = False

    # JSON: { "data": [...], "rules": {...} }
    if "application/json" in content_type:
        payload = await request.json()
        if "data" not in payload:
            raise HTTPException(status_code=400, detail="JSON body must include 'data' (list of rows).")
        rules_obj = payload.get("rules", {}) or {}
        include_csv = bool(payload.get("include_csv", False))

        df = pd.DataFrame(payload["data"])
        columns_before = [str(c) for c in df.columns]
        rows_before = int(len(df))

        cleaned_df, changes = clean_df(df, **rules_obj)

        resp = {
            "rows_before": rows_before,
            "rows_after": int(len(cleaned_df)),
            "columns_before": columns_before,
            "columns_after": [str(c) for c in cleaned_df.columns],
            "changes": changes,
            "cleaned_data": df_to_json_records(cleaned_df),
        }
        if include_csv:
            resp["csv"] = cleaned_df.to_csv(index=False)
        return resp

    # multipart: file=<csv> rules=<json string>
    if "multipart/form-data" in content_type:
        import json

        form = await request.form()

        up = form.get("file")
        if up is None or not hasattr(up, "filename"):
            raise HTTPException(status_code=400, detail="multipart form must include a CSV file field named 'file'.")

        upload: UploadFile = up  # type: ignore
        raw = await read_upload_bytes(upload)

        try:
            df = pd.read_csv(BytesIO(raw))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

        rules_json = form.get("rules")
        if rules_json:
            try:
                rules_obj = json.loads(str(rules_json))
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"rules must be valid JSON string: {e}")
        include_csv = str(form.get("include_csv", "")).lower() == "true"

        columns_before = [str(c) for c in df.columns]
        rows_before = int(len(df))

        cleaned_df, changes = clean_df(df, **rules_obj)

        resp = {
            "rows_before": rows_before,
            "rows_after": int(len(cleaned_df)),
            "columns_before": columns_before,
            "columns_after": [str(c) for c in cleaned_df.columns],
            "changes": changes,
            "cleaned_data": df_to_json_records(cleaned_df),
        }
        if include_csv:
            resp["csv"] = cleaned_df.to_csv(index=False)
        return resp

    raise HTTPException(status_code=415, detail="Unsupported Content-Type. Use application/json or multipart/form-data.")


@app.post("/extract/pdf")
async def extract_pdf_route(file: UploadFile = File(...), mode: str = "text"):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a .pdf file")
    raw = await read_upload_bytes(file)

    if mode not in ("text", "tables", "both"):
        raise HTTPException(status_code=400, detail="mode must be one of: text, tables, both")

    try:
        return extract_pdf(raw, mode=mode)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/summarize/logs")
async def summarize_logs_route(request: Request, top_k: int = 10):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        text = str(payload.get("text", ""))
    else:
        text = (await request.body()).decode("utf-8", errors="replace")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Provide log text in the body (or JSON {'text': ...}).")

    return summarize_logs(text, top_k=top_k)


# Serve demo UI
if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
