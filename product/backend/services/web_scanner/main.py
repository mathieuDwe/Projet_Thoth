import asyncio
import json
import re
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from shared.config import get_settings
from shared.http_client import ThothHttpClient

app = FastAPI(
    title="Thoth Web Scanner Service",
    description="OSINT service that scans websites for technologies, security headers, "
                "redirect chains, SSL certificates, and metadata.",
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
http_client = ThothHttpClient(service_name="web_scanner")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

TECH_PATTERNS = [
    {"name": "WordPress", "headers": {}, "html": [r"/wp-content/", r"/wp-includes/", r"<meta name=\"generator\" content=\"WordPress"]},
    {"name": "Cloudflare", "headers": {"server": "cloudflare", "cf-ray": "."}, "html": []},
    {"name": "Nginx", "headers": {"server": "nginx"}, "html": []},
    {"name": "Apache", "headers": {"server": "apache"}, "html": []},
    {"name": "Cloudflare", "headers": {"cf-ray": "."}, "html": []},
    {"name": "LiteSpeed", "headers": {"server": "litespeed"}, "html": []},
    {"name": "OpenResty", "headers": {"server": "openresty"}, "html": []},
    {"name": "IIS", "headers": {"server": "microsoft-iis"}, "html": []},
    {"name": "Node.js", "headers": {"server": "node.js", "x-powered-by": "express"}, "html": []},
    {"name": "Django", "headers": {"server": "wsgi", "x-powered-by": "django"}, "html": []},
    {"name": "Ruby on Rails", "headers": {"server": "rails", "x-powered-by": "rails"}, "html": []},
    {"name": "PHP", "headers": {"x-powered-by": "php"}, "html": []},
    {"name": "Google Cloud", "headers": {"via": "google"}, "html": []},
    {"name": "AWS", "headers": {"server": "amazons3", "x-amz-": "."}, "html": []},
    {"name": "Varnish", "headers": {"via": "varnish", "x-varnish": "."}, "html": []},
    {"name": "Netlify", "headers": {"server": "netlify"}, "html": []},
    {"name": "Vercel", "headers": {"server": "vercel"}, "html": []},
    {"name": "GitHub Pages", "headers": {"server": "github.com"}, "html": []},
    {"name": "Shields.io", "headers": {}, "html": [r"<meta name=\"generator\" content=\"Shields"]},
    {"name": "Drupal", "headers": {}, "html": [r"/sites/default/", r"<meta name=\"generator\" content=\"Drupal"]},
    {"name": "Joomla", "headers": {}, "html": [r"/components/", r"/modules/", r"<meta name=\"generator\" content=\"Joomla"]},
    {"name": "Shopify", "headers": {"x-shopid": "."}, "html": [r"/cdn.shopify.com/"]},
    {"name": "Magento", "headers": {}, "html": [r"/skin/frontend/", r"<meta name=\"generator\" content=\"Magento"]},
    {"name": "Wix", "headers": {}, "html": [r"static.wixstatic.com", r"<meta name=\"generator\" content=\"Wix"]},
    {"name": "Squarespace", "headers": {}, "html": [r"static1.squarespace.com", r"<meta name=\"generator\" content=\"Squarespace"]},
    {"name": "React", "headers": {}, "html": [r"react", r"__NEXT_DATA__", r"__NEXT_LOADED_PAGES__"]},
    {"name": "Vue.js", "headers": {}, "html": [r"vuejs", r"__VUE__"]},
    {"name": "Angular", "headers": {}, "html": [r"ng-version", r"angular"]},
    {"name": "Bootstrap", "headers": {}, "html": [r"bootstrap", r"maxcdn.bootstrapcdn.com"]},
    {"name": "Tailwind CSS", "headers": {}, "html": [r"tailwindcss", r"cdn.tailwindcss"]},
    {"name": "Google Analytics", "headers": {}, "html": [r"googletagmanager.com", r"google-analytics.com"]},
    {"name": "Cloudflare", "headers": {}, "html": [r"cloudflare.com/ajax/libs/"]},
    {"name": "jQuery", "headers": {}, "html": [r"jquery"]},
    {"name": "Font Awesome", "headers": {}, "html": [r"fontawesome", r"font-awesome"]},
]

SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "X-XSS-Protection",
    "Referrer-Policy",
    "Permissions-Policy",
    "Access-Control-Allow-Origin",
    "Cross-Origin-Embedder-Policy",
    "Cross-Origin-Opener-Policy",
    "Cross-Origin-Resource-Policy",
]


class UrlScanRequest(BaseModel):
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


class TechDetectRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class RedirectRequest(BaseModel):
    url: str
    max_follow: int = 10

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


def extract_title(html: str) -> str:
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def detect_technologies(headers: dict, html: str) -> list[dict]:
    detected = []
    headers_lower = {k.lower(): v for k, v in headers.items()}
    for tech in TECH_PATTERNS:
        found = False
        reasons = []
        for h_key, h_val in tech["headers"].items():
            for header_key, header_value in headers_lower.items():
                if h_key in header_key:
                    if h_val == "." or h_val in header_value.lower():
                        found = True
                        reasons.append(f"header:{header_key}={header_value[:50]}")
                        break
        for pattern in tech["html"]:
            if re.search(pattern, html, re.IGNORECASE):
                found = True
                reasons.append(f"html:{pattern}")
                break
        if found:
            detected.append({"name": tech["name"], "evidence": reasons})
    return detected


async def fetch_url(url: str, follow_redirects: bool = True) -> dict:
    result = {"url": url, "status_code": None, "headers": {}, "html": "", "redirect_chain": [], "error": None}
    chain = []
    current_url = url
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=follow_redirects) as client:
            resp = await client.get(current_url, headers={"User-Agent": USER_AGENT})
            chain.append({"url": str(resp.url), "status_code": resp.status_code})
            for r in resp.history:
                chain.insert(0, {"url": str(r.url), "status_code": r.status_code})
            result["url"] = str(resp.url)
            result["status_code"] = resp.status_code
            result["headers"] = dict(resp.headers)
            result["html"] = resp.text[:50000]
            result["redirect_chain"] = chain
    except httpx.ConnectError:
        result["error"] = "Connection failed"
    except httpx.TimeoutException:
        result["error"] = "Timeout"
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


@app.on_event("startup")
async def startup():
    pass


@app.get("/")
async def root():
    return {
        "service": "Thoth Web Scanner Service",
        "version": "1.0.0",
        "endpoints": ["GET /health", "POST /scan/url", "POST /scan/technologies", "POST /scan/redirects"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "web_scanner", "timestamp": datetime.utcnow().isoformat()}


@app.post("/scan/url")
async def scan_url(request: UrlScanRequest):
    try:
        data = await fetch_url(request.url)
        if data["error"]:
            return {"success": False, "data": data, "summary": f"Scan failed: {data['error']}"}

        title = extract_title(data["html"]) if data["html"] else ""
        techs = detect_technologies(data["headers"], data["html"])
        security = {h: data["headers"].get(h, "missing") for h in SECURITY_HEADERS}
        security_present = sum(1 for v in security.values() if v != "missing")

        result_data = {
            "target": request.url,
            "final_url": data["url"],
            "status_code": data["status_code"],
            "title": title,
            "security_headers": security,
            "security_headers_count": security_present,
            "redirect_chain": data["redirect_chain"],
            "headers": {k: v for k, v in data["headers"].items() if k.lower() not in ("set-cookie",)},
            "technologies": techs,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = [f"HTTP {data['status_code']}"]
        if title:
            parts.append(f'Title: "{title[:50]}"')
        if techs:
            parts.append(f"{len(techs)} technologies detected")
        if security_present:
            parts.append(f"{security_present}/{len(SECURITY_HEADERS)} security headers")
        summary = "; ".join(parts)

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"URL scan failed: {str(e)}")


@app.post("/scan/technologies")
async def scan_technologies(request: TechDetectRequest):
    try:
        data = await fetch_url(request.url)
        if data["error"]:
            return {"success": False, "data": {"target": request.url, "error": data["error"]}, "summary": f"Tech detection failed: {data['error']}"}

        title = extract_title(data["html"]) if data["html"] else ""
        techs = detect_technologies(data["headers"], data["html"])

        result_data = {
            "target": request.url,
            "title": title,
            "technologies": techs,
            "server_header": data["headers"].get("server", "N/A"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        tech_names = [t["name"] for t in techs]
        summary = f"Detected {len(techs)} technologies: {', '.join(tech_names[:5])}" if techs else "No specific technologies detected"
        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tech detection failed: {str(e)}")


@app.post("/scan/redirects")
async def scan_redirects(request: RedirectRequest):
    try:
        data = await fetch_url(request.url, follow_redirects=True)
        chain = data.get("redirect_chain", [])

        result_data = {
            "target": request.url,
            "redirect_count": len(chain),
            "chain": chain,
            "final_url": data.get("url", request.url),
            "final_status": data.get("status_code"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        summary = f"{len(chain)} redirect(s): {' → '.join(str(s.get('status_code', '?')) for s in chain)}" if chain else "No redirects"
        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Redirect scan failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007, reload=settings.debug)
