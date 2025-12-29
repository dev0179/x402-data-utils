from __future__ import annotations
from typing import Any, Dict
import re
from collections import Counter

ERROR_PATTERNS = [
    re.compile(r"\bERROR\b", re.IGNORECASE),
    re.compile(r"\bException\b"),
    re.compile(r"\bTraceback\b"),
    re.compile(r"\bFATAL\b", re.IGNORECASE),
]

def summarize_logs(text: str, top_k: int = 10) -> Dict[str, Any]:
    lines = [ln.rstrip("\n") for ln in text.splitlines()]
    if not lines:
        return {"lines": 0, "top_issues": [], "counts": {}}

    error_lines = []
    for ln in lines:
        if any(p.search(ln) for p in ERROR_PATTERNS):
            error_lines.append(ln)

    def signature(ln: str) -> str:
        ln2 = re.sub(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?Z?\b", "<ts>", ln)
        ln2 = re.sub(r"\b0x[0-9a-fA-F]+\b", "<hex>", ln2)
        ln2 = re.sub(r"\b\d+\b", "<n>", ln2)
        ln2 = re.sub(r"\s+", " ", ln2).strip()
        return ln2[:240]

    sigs = [signature(ln) for ln in error_lines] if error_lines else [signature(ln) for ln in lines]
    counts = Counter(sigs)

    top = [{"signature": sig, "count": int(c)} for sig, c in counts.most_common(top_k)]

    return {
        "lines": int(len(lines)),
        "error_like_lines": int(len(error_lines)),
        "top_issues": top,
        "counts": {"unique_signatures": int(len(counts))},
    }
