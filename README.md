# Invoice & Receipt PDF to Structured JSON

Extract structured fields (`vendor`, `invoice_no`, `date`, `currency`, `total`) from PDF invoice URLs or raw invoice text into clean JSON datasets.

## Features
- **Hybrid Extraction**: Zero-cost deterministic parsing for standard layouts, with LLM fallback for complex invoices.
- **Built-in Guardrails**: 5MB / 10-page PDF limit and per-run `maxItems` cap.
- **Pay-per-Result Ready**: Outputs one clean JSON record per invoice to the Apify Dataset.
