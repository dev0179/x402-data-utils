from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def default_validation_config() -> Dict[str, Any]:
    return {
        "required_columns": [],
        "no_empty_headers": True,
        "no_empty_rows": False,
        "no_empty_cells": False,
        "strip_whitespace": True,
        "max_rows": 50000,
        "max_cols": 200,
        "type_rules": {},
        "regex_rules": {},
        "enum_rules": {},
        "date_rules": {},
        "unique_rules": [],
        "range_rules": {},
        "no_negative_numbers": False,
        "include_csv": False,
        "sample_errors_limit": 200,
    }


def _is_empty(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and np.isnan(val):
        return True
    if isinstance(val, str):
        return val.strip() == ""
    return False


def _merge_config(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = base.copy()
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            merged = out[k].copy()
            merged.update(v)
            out[k] = merged
        else:
            out[k] = v
    return out


def _coerce_bool(val: Any) -> Tuple[Optional[bool], bool]:
    if _is_empty(val):
        return None, True
    if isinstance(val, bool):
        return val, True
    if isinstance(val, (int, float)) and not np.isnan(val):
        return bool(val), True
    if isinstance(val, str):
        v = val.strip().lower()
        if v in {"true", "t", "1", "yes", "y"}:
            return True, True
        if v in {"false", "f", "0", "no", "n"}:
            return False, True
    return None, False


def validate_csv_full(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _merge_config(default_validation_config(), config or {})
    errors_all: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {
        "empty_rows": 0,
        "empty_cells": 0,
        "invalid_types": {},
        "regex_failures": {},
        "duplicates": 0,
        "range_failures": {},
    }
    row_errors: Dict[int, List[str]] = {}

    def add_error(code: str, message: str, column: Optional[str] = None, row: Optional[int] = None, value: Any = None):
        errors_all.append({"code": code, "message": message, "column": column, "row": row, "value": value})
        if row is not None:
            row_errors.setdefault(row, []).append(message)

    # Strip whitespace if requested
    if cfg.get("strip_whitespace", True):
        for col in df.columns:
            if df[col].dtype == object or isinstance(df[col].dtype, pd.StringDtype):
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    # Header checks
    if cfg.get("no_empty_headers", True):
        for col in df.columns:
            if _is_empty(col) or (isinstance(col, str) and col.strip() == ""):
                add_error("EMPTY_HEADER", "Column header is empty", column=None, row=None, value=None)

    # Max rows/cols
    max_rows = cfg.get("max_rows")
    max_cols = cfg.get("max_cols")
    if max_rows and len(df) > max_rows:
        add_error("TOO_MANY_ROWS", f"Row count {len(df)} exceeds max_rows {max_rows}", column=None, row=None, value=len(df))
    if max_cols and len(df.columns) > max_cols:
        add_error("TOO_MANY_COLUMNS", f"Column count {len(df.columns)} exceeds max_cols {max_cols}", column=None, row=None, value=len(df.columns))

    # Required columns
    for col in cfg.get("required_columns") or []:
        if col not in df.columns:
            add_error("MISSING_COLUMN", f"Missing required column '{col}'", column=col, row=None, value=None)

    # Empty rows
    if cfg.get("no_empty_rows"):
        empty_mask = df.isna()
        if cfg.get("strip_whitespace", True):
            # treat empty strings as NaN-like
            empty_mask = empty_mask | df.applymap(_is_empty)
        all_empty = empty_mask.all(axis=1)
        stats["empty_rows"] = int(all_empty.sum())
        for idx in df.index[all_empty]:
            add_error("EMPTY_ROW", "Row is empty", row=int(idx), column=None, value=None)

    # Empty cells
    if cfg.get("no_empty_cells"):
        mask_empty = df.applymap(_is_empty)
        stats["empty_cells"] = int(mask_empty.sum().sum())
        coords = np.argwhere(mask_empty.values)
        for r, c in coords:
            add_error("EMPTY_CELL", "Cell is empty", row=int(df.index[r]), column=str(df.columns[c]), value=None)
    else:
        stats["empty_cells"] = 0

    # Type validation + min/max
    type_rules: Dict[str, Dict[str, Any]] = cfg.get("type_rules") or {}
    range_failures: Dict[str, int] = {}
    for col, rule in type_rules.items():
        if col not in df.columns:
            continue
        series = df[col]
        target_type = str(rule.get("type", "")).lower()
        min_v = rule.get("min")
        max_v = rule.get("max")
        invalid_mask = pd.Series(False, index=series.index)
        numeric_series: Optional[pd.Series] = None

        if target_type in {"int", "float"}:
            numeric_series = pd.to_numeric(series, errors="coerce")
            invalid_mask = series.notna() & numeric_series.isna()
            stats["invalid_types"][col] = int(invalid_mask.sum())
            for idx, val in series[invalid_mask].items():
                add_error("TYPE_INVALID", f"Cannot parse as {target_type}", column=col, row=int(idx), value=val)

            if numeric_series is not None:
                if min_v is not None:
                    below = numeric_series.notna() & (numeric_series < min_v)
                    range_failures[col] = range_failures.get(col, 0) + int(below.sum())
                    for idx, val in numeric_series[below].items():
                        add_error("RANGE_FAIL", f"Value {val} below min {min_v}", column=col, row=int(idx), value=val)
                if max_v is not None:
                    above = numeric_series.notna() & (numeric_series > max_v)
                    range_failures[col] = range_failures.get(col, 0) + int(above.sum())
                    for idx, val in numeric_series[above].items():
                        add_error("RANGE_FAIL", f"Value {val} above max {max_v}", column=col, row=int(idx), value=val)

        elif target_type == "bool":
            coerced = []
            invalid_rows = []
            for idx, val in series.items():
                bval, ok = _coerce_bool(val)
                if not ok:
                    invalid_rows.append((idx, val))
                coerced.append(bval)
            stats["invalid_types"][col] = len(invalid_rows)
            for idx, val in invalid_rows:
                add_error("TYPE_INVALID", "Cannot parse as bool", column=col, row=int(idx), value=val)
        elif target_type == "string":
            # strings are always acceptable
            pass

    stats["range_failures"] = range_failures

    # Regex validation
    regex_rules: Dict[str, Dict[str, Any]] = cfg.get("regex_rules") or {}
    for col, rule in regex_rules.items():
        if col not in df.columns:
            continue
        pattern = rule.get("pattern")
        if not pattern:
            continue
        required = bool(rule.get("required"))
        compiled = re.compile(pattern)
        fails = 0
        for idx, val in df[col].items():
            if _is_empty(val):
                if required:
                    add_error("MISSING_REQUIRED", f"Column '{col}' is required", column=col, row=int(idx), value=val)
                continue
            sval = str(val)
            if not compiled.match(sval):
                fails += 1
                add_error("REGEX_FAIL", f"Value does not match pattern", column=col, row=int(idx), value=sval)
        if fails:
            stats["regex_failures"][col] = fails

    # Enum validation
    enum_rules: Dict[str, Dict[str, Any]] = cfg.get("enum_rules") or {}
    for col, rule in enum_rules.items():
        if col not in df.columns:
            continue
        allowed = rule.get("allowed") or []
        required = bool(rule.get("required"))
        for idx, val in df[col].items():
            if _is_empty(val):
                if required:
                    add_error("MISSING_REQUIRED", f"Column '{col}' is required", column=col, row=int(idx), value=val)
                continue
            if val not in allowed:
                add_error("ENUM_FAIL", f"Value '{val}' not in allowed list", column=col, row=int(idx), value=val)

    # Date validation
    date_rules: Dict[str, Dict[str, Any]] = cfg.get("date_rules") or {}
    for col, rule in date_rules.items():
        if col not in df.columns:
            continue
        fmt = rule.get("format", "auto")
        required = bool(rule.get("required"))
        if fmt == "auto":
            parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
        else:
            parsed = pd.to_datetime(df[col], errors="coerce", format=fmt)
        for idx, (raw, parsed_val) in enumerate(zip(df[col], parsed)):
            real_idx = int(df.index[idx])
            if _is_empty(raw):
                if required:
                    add_error("MISSING_REQUIRED", f"Column '{col}' is required", column=col, row=real_idx, value=raw)
                continue
            if pd.isna(parsed_val):
                add_error("DATE_INVALID", f"Cannot parse date with format '{fmt}'", column=col, row=real_idx, value=raw)

    # Unique rules
    unique_rules: List[Dict[str, Any]] = cfg.get("unique_rules") or []
    for rule in unique_rules:
        cols = rule.get("columns") or []
        if not cols:
            continue
        missing = [c for c in cols if c not in df.columns]
        if missing:
            continue
        subset = df[cols].copy()
        if rule.get("case_insensitive"):
            for c in cols:
                subset[c] = subset[c].astype(str).str.lower()
        dup_mask = subset.duplicated(keep=False)
        dup_count = int(dup_mask.sum())
        if dup_count:
            stats["duplicates"] += dup_count
            for idx in df.index[dup_mask]:
                add_error(
                    "DUPLICATE_ROW",
                    f"Duplicate combination on {cols}",
                    column=",".join(cols),
                    row=int(idx),
                    value=tuple(df.loc[idx, cols]),
                )

    # Range rules (independent of type_rules)
    range_rules: Dict[str, Dict[str, Any]] = cfg.get("range_rules") or {}
    for col, rule in range_rules.items():
        if col not in df.columns:
            continue
        min_v = rule.get("min")
        max_v = rule.get("max")
        if min_v is None and max_v is None:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        below = numeric.notna() & (numeric < min_v) if min_v is not None else pd.Series(False, index=df.index)
        above = numeric.notna() & (numeric > max_v) if max_v is not None else pd.Series(False, index=df.index)
        for idx, val in numeric[below].items():
            add_error("RANGE_FAIL", f"Value {val} below min {min_v}", column=col, row=int(idx), value=val)
        for idx, val in numeric[above].items():
            add_error("RANGE_FAIL", f"Value {val} above max {max_v}", column=col, row=int(idx), value=val)

    # No negative numbers (across numeric cols)
    if cfg.get("no_negative_numbers"):
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        for col in numeric_cols:
            numeric = pd.to_numeric(df[col], errors="coerce")
            neg_mask = numeric.notna() & (numeric < 0)
            for idx, val in numeric[neg_mask].items():
                add_error("NEGATIVE_NUMBER", "Negative numbers not allowed", column=col, row=int(idx), value=val)

    error_limit = cfg.get("sample_errors_limit", 200) or 200
    error_count = len(errors_all)
    warning_count = len(warnings)
    csv_string: Optional[str] = None
    if cfg.get("include_csv"):
        df_out = df.copy()
        df_out["_errors"] = [", ".join(row_errors.get(int(idx), [])) if row_errors.get(int(idx)) else "" for idx in df.index]
        csv_string = df_out.to_csv(index=False)
    result = {
        "valid": error_count == 0,
        "row_count": int(len(df)),
        "columns": [str(c) for c in df.columns],
        "error_count": error_count,
        "warning_count": warning_count,
        "errors": errors_all[:error_limit],
        "warnings": warnings[:error_limit],
        "stats": stats,
    }
    if csv_string is not None:
        result["csv"] = csv_string
    return result


if __name__ == "__main__":
    # Lightweight self-check
    sample = pd.DataFrame(
        {
            "price": ["1.0", "-2", "abc"],
            "quantity": ["5", "x", "3"],
            "phone": ["12345", "555-555-5555", ""],
            "email": ["ok@test.com", "bad@", ""],
            "state": ["CA", "ZZ", ""],
            "date": ["2024-01-01", "not-a-date", ""],
        }
    )
    cfg = default_validation_config()
    cfg.update(
        {
            "no_empty_rows": True,
            "no_empty_cells": False,
            "type_rules": {"price": {"type": "float", "min": 0}, "quantity": {"type": "int", "min": 0}},
            "regex_rules": {
                "phone": {"pattern": r"^\+?[0-9()\-\s]{7,}$", "required": False},
                "email": {"pattern": r"^[^@\s]+@[^@\s]+\.[^@\s]+$", "required": False},
            },
            "enum_rules": {"state": {"allowed": ["CA", "IL", "TX"], "required": False}},
            "date_rules": {"date": {"format": "auto", "required": False}},
            "unique_rules": [{"columns": ["price", "quantity"], "case_insensitive": True}],
        }
    )
    out = validate_csv_full(sample, cfg)
    print(out)
