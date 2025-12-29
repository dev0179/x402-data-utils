from __future__ import annotations
from typing import Any, Dict, List
from io import BytesIO

def extract_pdf(file_bytes: bytes, mode: str = "text") -> Dict[str, Any]:
    """
    mode: "text" | "tables" | "both"
    Best-effort tables via pdfplumber; fallback to text via pypdf.
    """
    result: Dict[str, Any] = {"pages": 0, "text": "", "tables": []}

    try:
        import pdfplumber  # type: ignore
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            result["pages"] = len(pdf.pages)

            if mode in ("text", "both"):
                texts = []
                for p in pdf.pages:
                    texts.append(p.extract_text() or "")
                result["text"] = "\n\n".join(texts).strip()

            if mode in ("tables", "both"):
                tables: List[Dict[str, Any]] = []
                for i, p in enumerate(pdf.pages):
                    try:
                        t = p.extract_tables() or []
                        for table in t:
                            tables.append({"page": i + 1, "data": table})
                    except Exception:
                        continue
                result["tables"] = tables

        return result
    except Exception:
        pass

    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(BytesIO(file_bytes))
        result["pages"] = len(reader.pages)
        if mode in ("text", "both"):
            texts = []
            for page in reader.pages:
                texts.append(page.extract_text() or "")
            result["text"] = "\n\n".join(texts).strip()
        return result
    except Exception as e:
        raise ValueError(f"PDF extraction failed: {e}")
