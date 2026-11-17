import asyncio
import httpx
from apify import Actor

from src.extractor import InvoiceResult, parse_pdf_bytes, process_text


async def main() -> None:
    async with Actor:
        actor_input = await Actor.get_input() or {}
        pdf_urls: list[str] = actor_input.get("pdfUrls", [])
        raw_texts: list[str] = actor_input.get("rawTexts", [])
        max_items: int = int(actor_input.get("maxItems", 50))

        tasks_done = 0
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            for url in pdf_urls:
                if tasks_done >= max_items:
                    break
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    text = parse_pdf_bytes(resp.content)
                    res = await process_text(text, source=url)
                except Exception as exc:
                    res = InvoiceResult(source=url, error=str(exc))
                await Actor.push_data(res.model_dump())
                tasks_done += 1

        for idx, txt in enumerate(raw_texts):
            if tasks_done >= max_items:
                break
            try:
                res = await process_text(txt, source=f"raw_text_{idx}")
            except Exception as exc:
                res = InvoiceResult(source=f"raw_text_{idx}", error=str(exc))
            await Actor.push_data(res.model_dump())
            tasks_done += 1

        Actor.log.info(f"Processed {tasks_done} invoice(s).")


if __name__ == "__main__":
    asyncio.run(main())
