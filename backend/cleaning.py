from __future__ import annotations
from typing import Any, Dict, List, Optional, Literal, Tuple
import pandas as pd
import numpy as np

TypeName = Literal["int", "float", "string", "bool"]

def normalize_colname(c: str) -> str:
    c2 = c.strip().lower().replace(" ", "_")
    c2 = "".join(ch for ch in c2 if ch.isalnum() or ch == "_")
    while "__" in c2:
        c2 = c2.replace("__", "_")
    return c2

def coerce_series(s: pd.Series, t: TypeName) -> pd.Series:
    if t == "string":
        return s.astype("string")
    if t == "bool":
        def to_bool(x):
            if pd.isna(x):
                return np.nan
            if isinstance(x, bool):
                return x
            if isinstance(x, (int, float)) and not pd.isna(x):
                return bool(int(x))
            x2 = str(x).strip().lower()
            if x2 in {"true", "t", "1", "yes", "y"}:
                return True
            if x2 in {"false", "f", "0", "no", "n"}:
                return False
            return np.nan
        return s.map(to_bool)
    if t == "int":
        return pd.to_numeric(s, errors="coerce").round().astype("Int64")
    if t == "float":
        return pd.to_numeric(s, errors="coerce").astype("Float64")
    raise ValueError(f"Unknown type: {t}")

def cap_outliers_iqr(df: pd.DataFrame, col: str, k: float = 1.5) -> int:
    if col not in df.columns:
        return 0
    x = pd.to_numeric(df[col], errors="coerce")
    if x.dropna().empty:
        return 0
    q1 = x.quantile(0.25)
    q3 = x.quantile(0.75)
    iqr = q3 - q1
    if pd.isna(iqr) or iqr == 0:
        return 0
    lo = q1 - k * iqr
    hi = q3 + k * iqr
    before = x.copy()
    capped = x.clip(lower=lo, upper=hi)
    changed = int((before != capped).fillna(False).sum())
    df[col] = capped
    return changed

def validate_csv_df(
    df: pd.DataFrame,
    required_columns: Optional[List[str]] = None,
    types: Optional[Dict[str, TypeName]] = None,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "valid": True,
        "row_count": int(len(df)),
        "columns": [str(c) for c in df.columns],
        "errors": [],
        "warnings": [],
    }

    if required_columns:
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            report["valid"] = False
            report["errors"].append(f"Missing required columns: {missing}")

    if any(pd.isna(c) or str(c).strip() == "" for c in df.columns):
        report["valid"] = False
        report["errors"].append("CSV contains empty column headers.")

    if types:
        for col, t in types.items():
            if col not in df.columns:
                continue
            coerced = coerce_series(df[col], t)
            bad = int(coerced.isna().sum()) - int(pd.isna(df[col]).sum())
            if bad > 0:
                report["warnings"].append(f"Column '{col}': {bad} values could not be coerced to {t}.")

    return report

def clean_df(
    df: pd.DataFrame,
    *,
    normalize_columns: bool = True,
    trim_strings: bool = True,
    drop_empty_rows: bool = True,
    drop_empty_columns: bool = False,
    drop_columns: Optional[List[str]] = None,
    drop_nulls: bool = False,
    drop_nulls_subset: Optional[List[str]] = None,
    deduplicate: bool = True,
    dedupe_subset: Optional[List[str]] = None,
    coerce_types: Optional[Dict[str, TypeName]] = None,
    parse_dates: Optional[List[str]] = None,
    date_output_format: Literal["iso", "datetime"] = "iso",
    cap_outliers: Optional[Dict[str, Dict[str, float]]] = None,  # {"price": {"k": 1.5}}
    remove_negative_rows: bool = False,
    negative_columns: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    changes: Dict[str, Any] = {
        "trimmed_string_cells": 0,
        "dropped_empty_rows": 0,
        "dropped_empty_columns": 0,
        "dropped_columns": [],
        "dropped_null_rows": 0,
        "deduped_rows": 0,
        "type_coercions": {},
        "date_parses": {},
        "outliers_capped": {},
        "removed_negative_rows": 0,
    }

    if normalize_columns:
        df = df.copy()
        df.columns = [normalize_colname(str(c)) for c in df.columns]

    if trim_strings:
        trimmed = 0
        for c in df.columns:
            if df[c].dtype == object or str(df[c].dtype).startswith("string"):
                before = df[c].astype("string")
                after = before.str.strip()
                trimmed += int((before != after).fillna(False).sum())
                df[c] = after
        changes["trimmed_string_cells"] = trimmed

    if drop_empty_rows:
        before_n = len(df)
        tmp = df.replace({"": np.nan})
        df = df.loc[~tmp.isna().all(axis=1)].copy()
        changes["dropped_empty_rows"] = int(before_n - len(df))

    if drop_empty_columns:
        before_cols = set(df.columns)
        tmp = df.replace({"": np.nan})
        df = df.loc[:, ~tmp.isna().all(axis=0)].copy()
        after_cols = set(df.columns)
        dropped = list(before_cols - after_cols)
        changes["dropped_empty_columns"] = len(dropped)
        changes["dropped_columns"] = dropped

    if drop_columns:
        dropped_now = []
        for c in drop_columns:
            if c in df.columns:
                df = df.drop(columns=[c])
                dropped_now.append(c)
        changes["dropped_columns"] = changes.get("dropped_columns", []) + dropped_now

    if parse_dates:
        date_counts = {}
        for c in parse_dates:
            if c in df.columns:
                attempted = int(df[c].notna().sum())
                parsed = pd.to_datetime(df[c], errors="coerce", infer_datetime_format=True)
                df[c] = parsed
                parsed_count = int(df[c].notna().sum())
                date_counts[c] = {"attempted": attempted, "parsed": parsed_count}
        changes["date_parses"] = date_counts

    if coerce_types:
        coercions = {}
        for col, t in coerce_types.items():
            if col in df.columns:
                attempted = int(df[col].notna().sum())
                df[col] = coerce_series(df[col], t)
                kept = int(df[col].notna().sum())
                coercions[col] = {"attempted": attempted, "kept_nonnull": kept}
        changes["type_coercions"] = coercions

    if cap_outliers:
        capped_counts = {}
        for col, cfg in cap_outliers.items():
            k = float(cfg.get("k", 1.5))
            capped_counts[col] = cap_outliers_iqr(df, col, k=k)
        changes["outliers_capped"] = capped_counts

    if drop_nulls:
        before_n = len(df)
        if drop_nulls_subset:
            df = df.dropna(subset=drop_nulls_subset)
        else:
            df = df.dropna()
        changes["dropped_null_rows"] = int(before_n - len(df))

    if remove_negative_rows:
        target_cols = negative_columns or list(df.columns)
        # Try to coerce strings with commas to numeric for negative detection
        def to_num(series: pd.Series) -> pd.Series:
            if pd.api.types.is_numeric_dtype(series):
                return series
            return pd.to_numeric(series.astype(str).str.replace(",", ""), errors="coerce")

        numeric_cols = []
        for c in target_cols:
            if c in df.columns:
                numeric_cols.append(c)
        if numeric_cols:
            coerced = {c: to_num(df[c]) for c in numeric_cols}
            mask = pd.DataFrame(coerced).lt(0).any(axis=1)
            before_n = len(df)
            df = df.loc[~mask].copy()
            changes["removed_negative_rows"] = int(before_n - len(df))

    if deduplicate:
        before_n = len(df)
        df = df.drop_duplicates(subset=dedupe_subset, keep="first")
        changes["deduped_rows"] = int(before_n - len(df))

    if parse_dates and date_output_format == "iso":
        for c in parse_dates:
            if c in df.columns and np.issubdtype(df[c].dtype, np.datetime64):
                df[c] = df[c].dt.strftime("%Y-%m-%d")

    return df, changes
