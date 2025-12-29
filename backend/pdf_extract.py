from __future__ import annotations
from typing import Any, Dict
from io import BytesIO


def extract_pdf(file_bytes: bytes) -> Dict[str, Any]:
    """
    Extract plain text only. Tables have been removed by request.
    """
    result: Dict[str, Any] = {"pages": 0, "text": ""}

    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            result["pages"] = len(pdf.pages)
            texts = []
            for p in pdf.pages:
                texts.append(p.extract_text() or "")
            result["text"] = "\n\n".join(texts).strip()
        return result
    except Exception:
        pass

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(BytesIO(file_bytes))
        result["pages"] = len(reader.pages)
        texts = []
        for page in reader.pages:
            texts.append(page.extract_text() or "")
        result["text"] = "\n\n".join(texts).strip()
        return result
    except Exception as e:
        raise ValueError(f"PDF extraction failed: {e}")
