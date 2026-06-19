import asyncio
import json
import re
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
    title="Thoth Text Analyzer Service",
    description="OSINT service that extracts emails, URLs, IPs, phone numbers, crypto addresses, and other patterns from raw text.",
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
http_client = ThothHttpClient(service_name="text_analyzer")


class AnalyzeTextRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Text must be at least 3 characters")
        if len(v) > 100000:
            raise ValueError("Text too long (max 100000 characters)")
        return v


EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
URL_REGEX = re.compile(r"(https?://[^\s<>\"']+|www\.[^\s<>\"']+\.[a-zA-Z]{2,}[^\s<>\"']*)")
IP_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_REGEX = re.compile(r"\b(?:[a-fA-F0-9]{1,4}:){7}[a-fA-F0-9]{1,4}\b")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[\s\-\.]?)?\(?\d{2,4}\)?[\s\-\.]?\d{2,4}[\s\-\.]?\d{2,4}[\s\-\.]?\d{2,4}")
BTC_REGEX = re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b")
ETH_REGEX = re.compile(r"\b0x[a-fA-F0-9]{40}\b")
DOMAIN_REGEX = re.compile(r"\b([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b")


def is_valid_ip(ip: str) -> bool:
    try:
        import ipaddress
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def extract_email(text: str) -> list[str]:
    seen = set()
    results = []
    for m in EMAIL_REGEX.finditer(text):
        email = m.group(0).lower().strip()
        if email not in seen and "." in email.split("@")[-1] and len(email) <= 254:
            seen.add(email)
            results.append(email)
    return results


def extract_urls(text: str) -> list[dict]:
    seen = set()
    results = []
    for m in URL_REGEX.finditer(text):
        url = m.group(0).rstrip(".,;:!?\"')").strip()
        if url not in seen:
            seen.add(url)
            if not url.startswith("http"):
                url = "https://" + url
            domain = ""
            try:
                domain = urlparse(url).netloc
            except Exception:
                pass
            results.append({"url": url, "domain": domain})
    return results


def extract_ips(text: str) -> list[str]:
    seen = set()
    results = []
    for m in IP_REGEX.finditer(text):
        ip = m.group(0).strip()
        if ip not in seen and is_valid_ip(ip):
            seen.add(ip)
            results.append(ip)
    return results


def extract_phones(text: str) -> list[str]:
    seen = set()
    results = []
    for m in PHONE_REGEX.finditer(text):
        cleaned = re.sub(r"[\s\-\.\(\)]", "", m.group(0))
        if cleaned not in seen and len(cleaned) >= 7 and len(cleaned) <= 15:
            seen.add(cleaned)
            results.append(cleaned)
    return results


def extract_domains(text: str) -> list[str]:
    seen = set()
    results = []
    for m in DOMAIN_REGEX.finditer(text):
        domain = m.group(0).lower().strip().rstrip(".")
        if domain not in seen:
            parts = domain.split(".")
            tld = parts[-1]
            if len(tld) >= 2 and len(domain) > len(tld) + 1:
                seen.add(domain)
                results.append(domain)
    return results


def extract_crypto(text: str) -> dict:
    btcs = list(set(BTC_REGEX.findall(text)))
    eths = list(set(ETH_REGEX.findall(text)))
    result = {}
    if btcs:
        result["bitcoin"] = btcs
    if eths:
        result["ethereum"] = eths
    return result


async def enrich_ips(ips: list[str]) -> dict:
    enriched = {}
    for ip in ips:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"http://ip-api.com/json/{ip}", params={"fields": "country,regionName,city,isp"})
                if resp.status_code == 200:
                    data = resp.json()
                    enriched[ip] = data if data.get("status") == "success" else None
        except Exception:
            enriched[ip] = None
    return enriched


@app.on_event("startup")
async def startup():
    pass


@app.get("/")
async def root():
    return {
        "service": "Thoth Text Analyzer Service",
        "version": "1.0.0",
        "endpoints": ["GET /health", "POST /analyze/text", "POST /analyze/text-deep"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "text_analyzer", "timestamp": datetime.utcnow().isoformat()}


@app.post("/analyze/text")
async def analyze_text(request: AnalyzeTextRequest):
    try:
        emails = extract_email(request.text)
        urls = extract_urls(request.text)
        ips = extract_ips(request.text)
        phones = extract_phones(request.text)
        domains = extract_domains(request.text)
        crypto = extract_crypto(request.text)

        result_data = {
            "stats": {
                "emails": len(emails),
                "urls": len(urls),
                "ips": len(ips),
                "phones": len(phones),
                "domains": len(domains),
                "crypto": len(crypto.get("bitcoin", [])) + len(crypto.get("ethereum", [])),
            },
            "emails": emails,
            "urls": urls,
            "ips": ips,
            "phones": phones,
            "domains": domains,
            "crypto": crypto,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = [f"{k}: {v}" for k, v in result_data["stats"].items() if v > 0]
        summary = " · ".join(parts) if parts else "Aucune donnée extraite"

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text analysis failed: {str(e)}")


@app.post("/analyze/text-deep")
async def analyze_text_deep(request: AnalyzeTextRequest):
    try:
        emails = extract_email(request.text)
        urls = extract_urls(request.text)
        ips = extract_ips(request.text)
        phones = extract_phones(request.text)
        domains = extract_domains(request.text)
        crypto = extract_crypto(request.text)

        ip_info = {}
        if ips:
            ip_info = await enrich_ips(ips)

        result_data = {
            "stats": {
                "emails": len(emails),
                "urls": len(urls),
                "ips": len(ips),
                "phones": len(phones),
                "domains": len(domains),
                "crypto": len(crypto.get("bitcoin", [])) + len(crypto.get("ethereum", [])),
            },
            "emails": emails,
            "urls": urls,
            "ips": ips,
            "phones": phones,
            "domains": domains,
            "crypto": crypto,
            "ip_geolocation": ip_info,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = [f"{k}: {v}" for k, v in result_data["stats"].items() if v > 0]
        summary = " · ".join(parts) if parts else "Aucune donnée extraite"

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deep text analysis failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011, reload=settings.debug)
