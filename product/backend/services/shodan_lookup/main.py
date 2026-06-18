import asyncio
import json
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from shared.config import get_settings
from shared.http_client import ThothHttpClient

app = FastAPI(
    title="Thoth Shodan Lookup Service",
    description="OSINT service that queries the Shodan API for exposed devices, open ports, "
                "services, and vulnerabilities associated with IP addresses and domains.",
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
http_client = ThothHttpClient(service_name="shodan_lookup")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

SHODAN_API_BASE = "https://api.shodan.io"


class IPLookupRequest(BaseModel):
    ip: str

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        v = v.strip()
        import ipaddress
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("Invalid IP address")
        return v


class DomainLookupRequest(BaseModel):
    domain: str

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("Domain required")
        return v


class SearchRequest(BaseModel):
    query: str
    max_results: int = 10

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Query too short")
        return v


async def shodan_request(endpoint: str, params: dict = None) -> dict:
    api_key = settings.shodan_api_key
    if not api_key:
        return {"error": "SHODAN_API_KEY not configured. Add it in Settings > API Keys or in .env file."}

    if params is None:
        params = {}
    params["key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{SHODAN_API_BASE}{endpoint}", params=params)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                return {"error": "Invalid Shodan API key"}
            elif resp.status_code == 403:
                return {"error": "API key quota exceeded or access denied"}
            else:
                return {"error": f"Shodan API returned HTTP {resp.status_code}"}
    except httpx.ConnectError:
        return {"error": "Cannot connect to Shodan API"}
    except httpx.TimeoutException:
        return {"error": "Shodan API timeout"}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.on_event("startup")
async def startup():
    pass


@app.get("/")
async def root():
    return {
        "service": "Thoth Shodan Lookup Service",
        "version": "1.0.0",
        "endpoints": ["GET /health", "POST /lookup/ip", "POST /lookup/domain", "POST /search/query"],
    }


@app.get("/health")
async def health():
    api_key = settings.shodan_api_key
    return {
        "status": "healthy",
        "service": "shodan_lookup",
        "api_key_configured": bool(api_key),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/lookup/ip")
async def lookup_ip(request: IPLookupRequest):
    try:
        if not settings.shodan_api_key:
            return {"success": False, "data": None, "summary": "Clé API Shodan non configurée", "error": "missing_api_key"}

        data = await shodan_request(f"/shodan/host/{request.ip}")

        if "error" in data:
            return {"success": False, "data": None, "summary": data["error"], "error": data["error"]}

        ports = data.get("ports", [])
        services = []
        for item in data.get("data", []):
            services.append({
                "port": item.get("port"),
                "transport": item.get("transport", "tcp"),
                "product": item.get("product", ""),
                "version": item.get("version", ""),
                "org": item.get("org", ""),
                "isp": item.get("isp", ""),
                "hostnames": item.get("hostnames", []),
                "os": item.get("os", ""),
                "timestamp": item.get("timestamp", ""),
            })

        vulns = data.get("vulns", [])

        result_data = {
            "target": request.ip,
            "ip": request.ip,
            "hostnames": data.get("hostnames", []),
            "city": data.get("city", ""),
            "country": data.get("country_name", ""),
            "org": data.get("org", ""),
            "isp": data.get("isp", ""),
            "os": data.get("os", ""),
            "ports": ports,
            "port_count": len(ports),
            "services": services,
            "vulnerabilities": list(vulns) if isinstance(vulns, list) else [],
            "vuln_count": len(vulns) if isinstance(vulns, list) else 0,
            "last_update": data.get("last_update", ""),
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = [f"{len(ports)} port(s) ouvert(s)"]
        if data.get("hostnames"):
            parts.append(f"DNS: {', '.join(data['hostnames'][:3])}")
        if data.get("country_name"):
            parts.append(f"Pays: {data['country_name']}")
        if vulns:
            parts.append(f"{len(vulns)} vulnérabilité(s)")
        summary = " · ".join(parts)

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shodan IP lookup failed: {str(e)}")


@app.post("/lookup/domain")
async def lookup_domain(request: DomainLookupRequest):
    try:
        if not settings.shodan_api_key:
            return {"success": False, "data": None, "summary": "Clé API Shodan non configurée", "error": "missing_api_key"}

        data = await shodan_request(f"/dns/resolve", {"hostnames": request.domain})

        if "error" in data:
            return {"success": False, "data": None, "summary": data["error"]}

        ip = data.get(request.domain)
        if not ip:
            return {"success": False, "data": None, "summary": f"Domain {request.domain} not resolved"}

        host_data = await shodan_request(f"/shodan/host/{ip}")
        if "error" in host_data:
            return {"success": True, "data": {"target": request.domain, "resolved_ip": ip, "shodan_error": host_data["error"]}, "summary": f"Résolu vers {ip} mais données Shodan indisponibles"}

        ports = host_data.get("ports", [])
        services = []
        for item in host_data.get("data", []):
            services.append({
                "port": item.get("port"),
                "product": item.get("product", ""),
                "version": item.get("version", ""),
                "org": item.get("org", ""),
            })

        result_data = {
            "target": request.domain,
            "resolved_ip": ip,
            "hostnames": host_data.get("hostnames", []),
            "country": host_data.get("country_name", ""),
            "org": host_data.get("org", ""),
            "os": host_data.get("os", ""),
            "ports": ports,
            "port_count": len(ports),
            "services": services,
            "timestamp": datetime.utcnow().isoformat(),
        }

        summary = f"{request.domain} → {ip} · {len(ports)} port(s) ouvert(s)"
        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shodan domain lookup failed: {str(e)}")


@app.post("/search/query")
async def search_shodan(request: SearchRequest):
    try:
        if not settings.shodan_api_key:
            return {"success": False, "data": None, "summary": "Clé API Shodan non configurée", "error": "missing_api_key"}

        data = await shodan_request("/shodan/host/search", {
            "query": request.query,
            "limit": min(request.max_results, 100),
        })

        if "error" in data:
            return {"success": False, "data": None, "summary": data["error"]}

        matches = []
        for m in data.get("matches", []):
            matches.append({
                "ip": m.get("ip_str", ""),
                "port": m.get("port"),
                "product": m.get("product", ""),
                "version": m.get("version", ""),
                "org": m.get("org", ""),
                "hostnames": m.get("hostnames", []),
                "country": m.get("country_name", ""),
                "city": m.get("city", ""),
                "timestamp": m.get("timestamp", ""),
            })

        result_data = {
            "query": request.query,
            "total": data.get("total", 0),
            "count": len(matches),
            "matches": matches,
            "timestamp": datetime.utcnow().isoformat(),
        }

        summary = f"{data.get('total', 0)} résultat(s) trouvé(s) pour '{request.query}'"
        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shodan search failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8013, reload=settings.debug)
