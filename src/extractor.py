import io
import json
import os
import re
from typing import Any
import httpx
from pypdf import PdfReader
from pydantic import BaseModel


class InvoiceResult(BaseModel):
    source: str
    vendor: str | None = None
    invoice_no: str | None = None
    date: str | None = None
    currency: str = "USD"
    total: float | None = None
    extraction_mode: str = "local_regex"
    estimated_cost_usd: float = 0.0
    error: str | None = None


def parse_pdf_bytes(raw: bytes) -> str:
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("PDF exceeds 5MB limit")
    reader = PdfReader(io.BytesIO(raw))
    if len(reader.pages) > 10:
        raise ValueError("PDF exceeds 10-page limit")
    return "\n".join(p.extract_text() or "" for p in reader.pages)


def local_regex_extract(text: str, source: str) -> InvoiceResult | None:
    inv_match = re.search(r"(?:Invoice\s*(?:#|No\.?|Number)[:\s]*)([A-Z0-9\-]+)", text, re.I)
    date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", text)
    total_match = re.search(r"(?:Total|Amount\s+Due)[:\s]*\$?\s*([0-9,]+\.\d{2})", text, re.I)
    vendor_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), None)

    if inv_match and total_match:
        return InvoiceResult(
            source=source,
            vendor=vendor_line,
            invoice_no=inv_match.group(1),
            date=date_match.group(1) if date_match else None,
            currency="USD",
            total=float(total_match.group(1).replace(",", "")),
            extraction_mode="local_regex",
            estimated_cost_usd=0.0,
        )
    return None


async def llm_fallback_extract(text: str, source: str) -> InvoiceResult:
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    if not api_key:
        raise RuntimeError("LLM_API_KEY missing for complex layout fallback")

    prompt = (
        "Extract JSON with keys: vendor, invoice_no, date, currency, total (float).\n\n"
        f"INVOICE TEXT:\n{text[:6000]}"
    )
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            },
        )
        resp.raise_for_status()
        payload: dict[str, Any] = resp.json()
        data = json.loads(payload["choices"][0]["message"]["content"])
        return InvoiceResult(
            source=source,
            vendor=data.get("vendor"),
            invoice_no=data.get("invoice_no"),
            date=data.get("date"),
            currency=data.get("currency", "USD"),
            total=data.get("total"),
            extraction_mode=f"llm:{model}",
            estimated_cost_usd=0.003,
        )


async def process_text(text: str, source: str) -> InvoiceResult:
    res = local_regex_extract(text, source)
    if res is not None:
        return res
    return await llm_fallback_extract(text, source)
