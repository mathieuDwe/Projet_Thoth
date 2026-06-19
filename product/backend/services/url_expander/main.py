import asyncio
import json
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from shared.config import get_settings
from shared.http_client import ThothHttpClient

app = FastAPI(
    title="Thoth URL Expander Service",
    description="OSINT service that expands shortened URLs, follows redirect chains, and previews the final destination.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()
http_client = ThothHttpClient(service_name="url_expander")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

SHORTENER_DOMAINS = [
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly",
    "shorturl.at", "tiny.cc", "tr.im", "cli.gs", "short.cm", "shorte.st",
    "rebrand.ly", "cutt.ly", "soo.gd", "s.id", "rb.gy", "bl.ink", "snip.ly",
    "v.gd", "2.gp", "x.co", "lnkd.in", "db.tt", "amzn.to", "bitly.com",
    "tiny.one", "1link.co", "adf.ly", "bc.vc", "shrinke.me",
]


class ExpandUrlRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        if len(v) > 2000:
            raise ValueError("URL too long")
        return v


class ExpandPreviewRequest(BaseModel):
    url: str
    max_follow: int = 10

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        if len(v) > 2000:
            raise ValueError("URL too long")
        return v


def is_shortened(url: str) -> bool:
    try:
        domain = urlparse(url).netloc.lower()
        return any(s in domain for s in SHORTENER_DOMAINS)
    except Exception:
        return False


async def follow_redirect_chain(url: str, max_follow: int = 10) -> list[dict]:
    chain = []
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=False) as client:
            current_url = url
            for _ in range(max_follow + 1):
                resp = await client.get(current_url, headers={"User-Agent": USER_AGENT})
                chain.append({
                    "url": str(resp.url),
                    "status_code": resp.status_code,
                    "headers": {
                        "location": resp.headers.get("location", ""),
                        "content-type": resp.headers.get("content-type", ""),
                        "server": resp.headers.get("server", ""),
                    },
                })
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location", "")
                    if location:
                        current_url = location
                        continue
                break
    except httpx.ConnectError:
        if not chain:
            chain.append({"url": url, "status_code": 0, "headers": {}, "error": "Connection failed"})
    except httpx.TimeoutException:
        if not chain:
            chain.append({"url": url, "status_code": 0, "headers": {}, "error": "Timeout"})
    except Exception as e:
        if not chain:
            chain.append({"url": url, "status_code": 0, "headers": {}, "error": str(e)[:100]})
    return chain


async def preview_page(url: str) -> dict:
    preview = {"title": "", "description": "", "domain": "", "status_code": None}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            preview["status_code"] = resp.status_code
            preview["domain"] = urlparse(str(resp.url)).netloc
            html = resp.text[:50000]
            import re
            title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
            if title_m:
                preview["title"] = title_m.group(1).strip()
            desc_m = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html, re.IGNORECASE)
            if desc_m:
                preview["description"] = desc_m.group(1).strip()
    except Exception:
        pass
    return preview


@app.on_event("startup")
async def startup():
    pass


@app.get("/")
async def root():
    return {
        "service": "Thoth URL Expander Service",
        "version": "1.0.0",
        "endpoints": ["GET /health", "POST /expand/url", "POST /expand/preview"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "url_expander", "timestamp": datetime.utcnow().isoformat()}


@app.post("/expand/url")
async def expand_url(request: ExpandUrlRequest):
    try:
        chain = await follow_redirect_chain(request.url)
        is_short = is_shortened(request.url)

        result_data = {
            "target": request.url,
            "is_shortened": is_short,
            "redirect_count": len(chain) - 1,
            "chain": chain,
            "final_url": chain[-1]["url"] if chain else request.url,
            "final_status": chain[-1]["status_code"] if chain else None,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = []
        if is_short:
            parts.append("URL raccourcie")
        parts.append(f"{len(chain)} étape(s)")
        if chain:
            parts.append(f"→ {chain[-1]['url'][:60]}")
        summary = " · ".join(parts)

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL expand failed: {str(e)}")


@app.post("/expand/preview")
async def expand_preview(request: ExpandPreviewRequest):
    try:
        chain = await follow_redirect_chain(request.url, request.max_follow)
        final_url = chain[-1]["url"] if chain else request.url
        preview = await preview_page(final_url)

        result_data = {
            "target": request.url,
            "is_shortened": is_shortened(request.url),
            "redirect_count": len(chain) - 1,
            "chain": chain,
            "final_url": final_url,
            "final_status": chain[-1]["status_code"] if chain else None,
            "preview": preview,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = [f"{len(chain)} étape(s)"]
        if preview.get("title"):
            parts.append(f'"{preview["title"][:50]}"')
        if preview.get("domain"):
            parts.append(preview["domain"])
        summary = " · ".join(parts)

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL preview failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012, reload=settings.debug)
