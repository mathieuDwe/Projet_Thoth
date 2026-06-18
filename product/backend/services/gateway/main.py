import asyncio
import json
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response, StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import init_db, get_session, get_async_session
from shared.models import Report, User
from shared.http_client import ThothHttpClient
from services.gateway.auth import router as auth_router, get_current_user

app = FastAPI(
    title="Thoth Gateway - OSINT Platform API",
    description="Central gateway for the Thoth OSINT Platform. Aggregates results from Breach Lookup, "
                "Social Harvester, DNS Investigator, and IP Geolocation microservices into unified reports.",
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
http_client = ThothHttpClient(service_name="gateway")

# Inclure le routeur d'authentification
app.include_router(auth_router)

# Microservice URLs (use Docker service names in container, localhost for dev)
import os
SERVICE_BREACH = os.getenv("SERVICE_BREACH_URL", "http://localhost:8001")
SERVICE_SOCIAL = os.getenv("SERVICE_SOCIAL_URL", "http://localhost:8002")
SERVICE_DNS = os.getenv("SERVICE_DNS_URL", "http://localhost:8003")
SERVICE_IP = os.getenv("SERVICE_IP_URL", "http://localhost:8004")
SERVICE_PERSON_FINDER = os.getenv("SERVICE_PERSON_FINDER_URL", "http://localhost:8005")
SERVICE_EMAIL_INVESTIGATOR = os.getenv("SERVICE_EMAIL_INVESTIGATOR_URL", "http://localhost:8006")
SERVICE_WEB_SCANNER = os.getenv("SERVICE_WEB_SCANNER_URL", "http://localhost:8007")
SERVICE_WAYBACK_MACHINE = os.getenv("SERVICE_WAYBACK_MACHINE_URL", "http://localhost:8008")
SERVICE_IMAGE_SEARCH = os.getenv("SERVICE_IMAGE_SEARCH_URL", "http://localhost:8009")
SERVICE_PHONE_ANALYZER = os.getenv("SERVICE_PHONE_ANALYZER_URL", "http://localhost:8010")
SERVICE_TEXT_ANALYZER = os.getenv("SERVICE_TEXT_ANALYZER_URL", "http://localhost:8011")
SERVICE_URL_EXPANDER = os.getenv("SERVICE_URL_EXPANDER_URL", "http://localhost:8012")
SERVICE_SHODAN_LOOKUP = os.getenv("SERVICE_SHODAN_LOOKUP_URL", "http://localhost:8013")

SERVICE_TIMEOUT = 30.0

EXPORT_DIR = settings.report_storage_path or "/tmp/thoth_exports"


class GlobalInvestigateRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    domain: Optional[str] = None
    ip: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().lower()
            import re
            if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", v):
                raise ValueError("Invalid email format")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip().lower()
            import re
            if not re.match(r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$", v):
                raise ValueError("Invalid domain format")
        return v

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: Optional[str]) -> Optional[str]:
        if v:
            v = v.strip()
            import ipaddress
            try:
                ipaddress.ip_address(v)
            except ValueError:
                raise ValueError("Invalid IP address format")
        return v


class ReportQueryParams(BaseModel):
    service: Optional[str] = None
    target: Optional[str] = None
    severity: Optional[str] = None
    limit: int = 50
    offset: int = 0


async def call_microservice(service_url: str, endpoint: str, payload: dict) -> dict:
    """Call a microservice endpoint and return structured result."""
    result = {"service": service_url.split("://")[1].split(":")[0], "success": False, "data": None, "error": None}
    try:
        async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
            resp = await client.post(
                f"{service_url}{endpoint}",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                result["success"] = True
                result["data"] = data.get("data")
                result["summary"] = data.get("summary")
            else:
                result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
    except httpx.ConnectError:
        result["error"] = "Service unreachable"
    except httpx.TimeoutException:
        result["error"] = "Service timeout"
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


async def generate_markdown_report(consolidated: dict) -> str:
    """Generate a markdown-formatted report from consolidated data."""
    lines = []
    lines.append("# Thoth OSINT Investigation Report")
    lines.append(f"\n**Generated:** {datetime.utcnow().isoformat()}")
    lines.append(f"**Targets:** {', '.join(filter(None, [consolidated.get(k) for k in ('email', 'username', 'domain', 'ip')]))}")
    lines.append("\n---\n")

    for service_key, service_data in consolidated.get("results", {}).items():
        lines.append(f"## {service_key.replace('_', ' ').title()}")
        if service_data.get("error"):
            lines.append(f"\n⚠ **Error:** {service_data['error']}\n")
            continue
        if service_data.get("data"):
            lines.append(f"\n**Summary:** {service_data.get('summary', 'N/A')}\n")
            lines.append("```json")
            lines.append(json.dumps(service_data["data"], indent=2, default=str)[:2000])
            lines.append("```\n")
        else:
            lines.append("\n*No data collected*\n")
        lines.append("---\n")

    if consolidated.get("score") is not None:
        lines.append(f"\n**Overall Score:** {consolidated['score']}/10")
        lines.append(f"\n**Overall Severity:** {consolidated['severity']}")

    return "\n".join(lines)


def _build_markdown_report(report) -> str:
    """Build a formatted markdown report from a Report object."""
    lines = []
    lines.append("# Thoth OSINT Report")
    lines.append(f"\n**Target:** {report.target}")
    lines.append(f"**Service:** {report.service}")
    lines.append(f"**Date:** {report.created_at.isoformat() if report.created_at else 'N/A'}")
    lines.append(f"**Severity:** {report.severity}")
    lines.append(f"**Score:** {report.score}/10")
    lines.append("\n---\n")

    if report.summary:
        lines.append("## Summary\n")
        lines.append(report.summary)
        lines.append("\n---\n")

    # Microservice results
    data = report.data or {}
    results = data.get("results", {})
    if results:
        lines.append("## Investigation Results\n")
        for svc_name, svc_data in results.items():
            label = svc_name.replace("_", " ").title()
            lines.append(f"### {label}\n")
            if svc_data.get("success"):
                lines.append(f"**Status:** ✅ Success\n")
                if svc_data.get("summary"):
                    lines.append(f"{svc_data['summary']}\n")
                if svc_data.get("data"):
                    lines.append("```json")
                    lines.append(json.dumps(svc_data["data"], indent=2, default=str)[:3000])
                    lines.append("```\n")
            else:
                lines.append(f"**Status:** ❌ Failed\n")
                lines.append(f"**Error:** {svc_data.get('error', 'Unknown')}\n")
            lines.append("---\n")

    lines.append(f"\n*Generated by Thoth OSINT Platform on {datetime.utcnow().isoformat()}*")
    return "\n".join(lines)


@app.on_event("startup")
async def startup():
    await init_db()
    os.makedirs(EXPORT_DIR, exist_ok=True)


@app.get("/")
async def root():
    return {
        "service": "Thoth Gateway - OSINT Platform API",
        "version": "1.0.0",
        "endpoints": [
            "POST /auth/register",
            "POST /auth/login",
            "GET /auth/me",
            "GET /health",
            "GET /status",
            "GET /dashboard/stats",
            "GET /dashboard/services",
            "GET /dashboard/activity",
            "GET /settings",
            "PATCH /settings/password",
            "PUT /settings/api-keys",
            "POST /investigate/global",
            "GET /reports",
            "GET /reports/{id}",
            "DELETE /reports/{id}",
            "GET /reports/{id}/export",
        "POST /person-finder/search",
        "POST /person-finder/images",
        "POST /person-finder/articles",
        "POST /email-investigator/analyze",
        "POST /email-investigator/domain-mx",
        "POST /web-scanner/scan",
        "POST /web-scanner/redirects",
        "POST /wayback-machine/snapshots",
        "POST /wayback-machine/available",
        "POST /image-search/reverse",
        "POST /image-search/metadata",
        "POST /image-search/analyze",
        "POST /phone-analyzer/analyze",
        "POST /text-analyzer/analyze",
        "POST /text-analyzer/deep",
        "POST /url-expander/expand",
        "POST /url-expander/preview",
        "POST /shodan-lookup/ip",
        "POST /shodan-lookup/domain",
        "POST /shodan-lookup/query",
        ],
        "microservices": {
            "breach_lookup": f"{SERVICE_BREACH}/health",
            "social_harvester": f"{SERVICE_SOCIAL}/health",
            "dns_investigator": f"{SERVICE_DNS}/health",
            "ip_geoloc": f"{SERVICE_IP}/health",
            "person_finder": f"{SERVICE_PERSON_FINDER}/health",
        "email_investigator": f"{SERVICE_EMAIL_INVESTIGATOR}/health",
        "web_scanner": f"{SERVICE_WEB_SCANNER}/health",
        "wayback_machine": f"{SERVICE_WAYBACK_MACHINE}/health",
        "image_search": f"{SERVICE_IMAGE_SEARCH}/health",
        "phone_analyzer": f"{SERVICE_PHONE_ANALYZER}/health",
        "text_analyzer": f"{SERVICE_TEXT_ANALYZER}/health",
        "url_expander": f"{SERVICE_URL_EXPANDER}/health",
        "shodan_lookup": f"{SERVICE_SHODAN_LOOKUP}/health",
        },
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gateway", "timestamp": datetime.utcnow().isoformat()}


@app.get("/status")
async def status():
    """Check health status of all microservices."""
    services = {
        "breach_lookup": f"{SERVICE_BREACH}/health",
        "social_harvester": f"{SERVICE_SOCIAL}/health",
        "dns_investigator": f"{SERVICE_DNS}/health",
        "ip_geoloc": f"{SERVICE_IP}/health",
        "person_finder": f"{SERVICE_PERSON_FINDER}/health",
        "email_investigator": f"{SERVICE_EMAIL_INVESTIGATOR}/health",
        "web_scanner": f"{SERVICE_WEB_SCANNER}/health",
        "wayback_machine": f"{SERVICE_WAYBACK_MACHINE}/health",
        "image_search": f"{SERVICE_IMAGE_SEARCH}/health",
        "phone_analyzer": f"{SERVICE_PHONE_ANALYZER}/health",
        "text_analyzer": f"{SERVICE_TEXT_ANALYZER}/health",
        "url_expander": f"{SERVICE_URL_EXPANDER}/health",
        "shodan_lookup": f"{SERVICE_SHODAN_LOOKUP}/health",
    }

    async def check_service(name: str, url: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                return {"name": name, "status": "healthy" if resp.status_code == 200 else "degraded", "code": resp.status_code}
        except Exception:
            return {"name": name, "status": "down", "code": None}

    tasks = [check_service(name, url) for name, url in services.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    service_statuses = []
    for r in results:
        if isinstance(r, Exception):
            service_statuses.append({"status": "error", "error": str(r)})
        else:
            service_statuses.append(r)

    all_healthy = all(s.get("status") == "healthy" for s in service_statuses)
    overall = "healthy" if all_healthy else "degraded"

    return {
        "overall": overall,
        "services": {s["name"]: {"status": s["status"], "code": s.get("code")} for s in service_statuses},
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/dashboard/stats")
async def dashboard_stats(session: AsyncSession = Depends(get_session)):
    """Return aggregated dashboard statistics."""
    from sqlalchemy import func, select

    # Get total report count
    count_result = await session.execute(select(func.count(Report.id)))
    total_requests = count_result.scalar() or 0

    # Get severity breakdown
    severity_result = await session.execute(
        select(Report.severity, func.count(Report.id)).group_by(Report.severity)
    )
    severity_counts = dict(severity_result.all())

    # Compute success rate (reports with score > 0 are "successful")
    success_count_result = await session.execute(
        select(func.count(Report.id)).where(Report.score > 0)
    )
    success_count = success_count_result.scalar() or 0
    success_rate = (success_count / total_requests * 100) if total_requests > 0 else 100.0

    # Active services from /status
    from shared.http_client import ThothHttpClient
    client = ThothHttpClient(service_name="gateway")
    active_services = 0
    for svc_url in [SERVICE_BREACH, SERVICE_SOCIAL, SERVICE_DNS, SERVICE_IP, SERVICE_PERSON_FINDER, SERVICE_EMAIL_INVESTIGATOR, SERVICE_WEB_SCANNER, SERVICE_WAYBACK_MACHINE, SERVICE_IMAGE_SEARCH, SERVICE_PHONE_ANALYZER, SERVICE_TEXT_ANALYZER, SERVICE_URL_EXPANDER, SERVICE_SHODAN_LOOKUP]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                resp = await c.get(f"{svc_url}/health")
                if resp.status_code == 200:
                    active_services += 1
        except Exception:
            pass

    alerts = severity_counts.get("critical", 0) + severity_counts.get("high", 0)

    return {
        "totalRequests": total_requests,
        "successRate": round(success_rate, 1),
        "activeServices": active_services,
        "alerts": alerts,
    }


@app.get("/dashboard/services")
async def dashboard_services():
    """Return the status of all microservices for the dashboard."""
    services_list = [
        {"name": "API Gateway", "type": "Core", "status": "online"},
        {"name": "DNS Investigator", "type": "Recon", "status": "online"},
        {"name": "WHOIS Lookup", "type": "Recon", "status": "online"},
        {"name": "Social Harvester", "type": "Threat Intel", "status": "online"},
        {"name": "Breach Lookup", "type": "Threat Intel", "status": "online"},
        {"name": "IP Geolocation", "type": "Recon", "status": "online"},
        {"name": "Person Finder", "type": "Recon", "status": "online"},
        {"name": "Email Investigator", "type": "Recon", "status": "online"},
        {"name": "Web Scanner", "type": "Recon", "status": "online"},
        {"name": "Wayback Machine", "type": "Recon", "status": "online"},
        {"name": "Image Search", "type": "Recon", "status": "online"},
        {"name": "Phone Analyzer", "type": "Recon", "status": "online"},
        {"name": "Text Analyzer", "type": "Utils", "status": "online"},
        {"name": "URL Expander", "type": "Utils", "status": "online"},
        {"name": "Shodan Lookup", "type": "Recon", "status": "online"},
    ]

    service_urls = {
        "DNS Investigator": SERVICE_DNS,
        "Breach Lookup": SERVICE_BREACH,
        "Social Harvester": SERVICE_SOCIAL,
        "IP Geolocation": SERVICE_IP,
        "Person Finder": SERVICE_PERSON_FINDER,
        "Email Investigator": SERVICE_EMAIL_INVESTIGATOR,
        "Web Scanner": SERVICE_WEB_SCANNER,
        "Wayback Machine": SERVICE_WAYBACK_MACHINE,
        "Image Search": SERVICE_IMAGE_SEARCH,
        "Phone Analyzer": SERVICE_PHONE_ANALYZER,
        "Text Analyzer": SERVICE_TEXT_ANALYZER,
        "URL Expander": SERVICE_URL_EXPANDER,
        "Shodan Lookup": SERVICE_SHODAN_LOOKUP,
    }

    async def check(svc_name: str, url: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=3.0) as c:
                resp = await c.get(f"{url}/health")
                return "online" if resp.status_code == 200 else "degraded"
        except Exception:
            return "offline"

    tasks = [check(name, url) for name, url in service_urls.items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    status_map = dict(zip(service_urls.keys(), results))
    for svc in services_list:
        if svc["name"] in status_map:
            svc["status"] = status_map[svc["name"]] if not isinstance(status_map[svc["name"]], Exception) else "offline"

    return services_list


@app.get("/dashboard/activity")
async def dashboard_activity(session: AsyncSession = Depends(get_session)):
    """Return recent activity feed from reports."""
    from sqlalchemy import select

    stmt = select(Report).order_by(Report.created_at.desc()).limit(20)
    result = await session.execute(stmt)
    recent_reports = result.scalars().all()

    activities = []
    for report in recent_reports:
        activities.append({
            "id": report.id,
            "type": "investigation",
            "target": report.target,
            "service": report.service,
            "severity": report.severity,
            "score": report.score,
            "timestamp": report.created_at.isoformat() if report.created_at else None,
            "summary": report.summary[:100] if report.summary else "",
        })

    return activities


# ──────────────────────────────────────────────
# Endpoints Paramètres
# ──────────────────────────────────────────────


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Le mot de passe doit contenir au moins 6 caractères")
        return v


class UpdateApiKeysRequest(BaseModel):
    shodan_api_key: Optional[str] = ""
    virustotal_api_key: Optional[str] = ""
    abuseipdb_api_key: Optional[str] = ""
    ipinfo_api_key: Optional[str] = ""



@app.post("/person-finder/search")
async def person_finder_search(request: GlobalInvestigateRequest):
    """Proxy to person_finder service for person search."""
    if not request.username and not request.email:
        raise HTTPException(status_code=400, detail="username or email required")
    return await call_microservice(SERVICE_PERSON_FINDER, "/search/person", {"name": request.username or request.email})


@app.post("/person-finder/images")
async def person_finder_images(request: GlobalInvestigateRequest):
    """Proxy to person_finder service for image search."""
    target = request.username or request.email
    if not target:
        raise HTTPException(status_code=400, detail="username or email required")
    return await call_microservice(SERVICE_PERSON_FINDER, "/search/images", {"query": target})


@app.post("/person-finder/articles")
async def person_finder_articles(request: GlobalInvestigateRequest):
    """Proxy to person_finder service for article search."""
    target = request.username or request.email
    if not target:
        raise HTTPException(status_code=400, detail="username or email required")
    return await call_microservice(SERVICE_PERSON_FINDER, "/search/articles", {"query": target})


@app.post("/email-investigator/analyze")
async def email_investigator_analyze(request: GlobalInvestigateRequest):
    """Proxy to email_investigator service for email analysis."""
    if not request.email:
        raise HTTPException(status_code=400, detail="email required")
    return await call_microservice(SERVICE_EMAIL_INVESTIGATOR, "/analyze/email", {"email": request.email})


@app.post("/email-investigator/domain-mx")
async def email_investigator_domain_mx(request: GlobalInvestigateRequest):
    """Proxy to email_investigator service for domain MX analysis."""
    target = request.email or request.domain
    if not target:
        raise HTTPException(status_code=400, detail="email or domain required")
    domain = target.split("@")[1] if "@" in target else target
    return await call_microservice(SERVICE_EMAIL_INVESTIGATOR, "/analyze/domain-mx", {"domain": domain})


@app.post("/web-scanner/scan")
async def web_scanner_scan(request: GlobalInvestigateRequest):
    """Proxy to web_scanner service for URL scan."""
    target = request.domain or request.email
    if not target:
        raise HTTPException(status_code=400, detail="domain or email required")
    url = f"https://{target}" if not target.startswith(("http://", "https://")) else target
    return await call_microservice(SERVICE_WEB_SCANNER, "/scan/url", {"url": url})


@app.post("/web-scanner/redirects")
async def web_scanner_redirects(request: GlobalInvestigateRequest):
    """Proxy to web_scanner service for redirect chain."""
    target = request.domain or request.email
    if not target:
        raise HTTPException(status_code=400, detail="domain or email required")
    url = f"https://{target}" if not target.startswith(("http://", "https://")) else target
    return await call_microservice(SERVICE_WEB_SCANNER, "/scan/redirects", {"url": url})


@app.post("/wayback-machine/snapshots")
async def wayback_machine_snapshots(request: GlobalInvestigateRequest):
    """Proxy to wayback_machine service for URL snapshots."""
    target = request.domain or request.email
    if not target:
        raise HTTPException(status_code=400, detail="domain or email required")
    url = f"https://{target}" if not target.startswith(("http://", "https://")) else target
    return await call_microservice(SERVICE_WAYBACK_MACHINE, "/archive/snapshots", {"url": url})


@app.post("/wayback-machine/available")
async def wayback_machine_available(request: GlobalInvestigateRequest):
    """Proxy to wayback_machine service for availability check."""
    target = request.domain or request.email
    if not target:
        raise HTTPException(status_code=400, detail="domain or email required")
    url = f"https://{target}" if not target.startswith(("http://", "https://")) else target
    return await call_microservice(SERVICE_WAYBACK_MACHINE, "/archive/available", {"url": url})


@app.post("/image-search/reverse")
async def image_search_reverse(request: GlobalInvestigateRequest):
    """Proxy to image_search service for reverse image search."""
    target = request.domain or request.email
    if not target:
        raise HTTPException(status_code=400, detail="domain or email required")
    image_url = f"https://{target}" if not target.startswith(("http://", "https://")) else target
    return await call_microservice(SERVICE_IMAGE_SEARCH, "/search/reverse", {"image_url": image_url})


@app.post("/image-search/metadata")
async def image_search_metadata(request: GlobalInvestigateRequest):
    """Proxy to image_search service for image metadata."""
    target = request.domain or request.email
    if not target:
        raise HTTPException(status_code=400, detail="domain or email required")
    image_url = f"https://{target}" if not target.startswith(("http://", "https://")) else target
    return await call_microservice(SERVICE_IMAGE_SEARCH, "/search/metadata", {"image_url": image_url})


@app.post("/image-search/analyze")
async def image_search_analyze(request: Request):
    """Proxy to image_search service for image analysis (supports file upload)."""
    try:
        body = await request.form()
        files = {}
        data = {}
        for field, value in body.items():
            if hasattr(value, "read"):
                files["file"] = (value.filename, value.file, getattr(value, "content_type", "image/jpeg"))
            else:
                data[field] = value

        async with httpx.AsyncClient(timeout=SERVICE_TIMEOUT) as client:
            if files:
                resp = await client.post(
                    f"{SERVICE_IMAGE_SEARCH}/search/analyze",
                    data=data,
                    files=files,
                )
            else:
                resp = await client.post(
                    f"{SERVICE_IMAGE_SEARCH}/search/analyze",
                    json=data,
                )

            if resp.status_code == 200:
                result = resp.json()
                return {
                    "service": "image-search",
                    "success": result.get("success", False),
                    "data": result.get("data"),
                    "summary": result.get("summary"),
                    "error": result.get("error"),
                }
            else:
                return {
                    "service": "image-search",
                    "success": False,
                    "data": None,
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                }
    except Exception as e:
        return {"service": "image-search", "success": False, "data": None, "error": str(e)[:200]}


@app.post("/phone-analyzer/analyze")
async def phone_analyze(request: GlobalInvestigateRequest):
    """Proxy to phone_analyzer service."""
    if not request.username:
        raise HTTPException(status_code=400, detail="username (phone number) required")
    return await call_microservice(SERVICE_PHONE_ANALYZER, "/analyze/phone", {"phone": request.username})


@app.post("/text-analyzer/analyze")
async def text_analyze(request: GlobalInvestigateRequest):
    """Proxy to text_analyzer service."""
    if not request.username:
        raise HTTPException(status_code=400, detail="text required")
    return await call_microservice(SERVICE_TEXT_ANALYZER, "/analyze/text", {"text": request.username})


@app.post("/text-analyzer/deep")
async def text_analyze_deep(request: GlobalInvestigateRequest):
    """Proxy to text_analyzer service with IP enrichment."""
    if not request.username:
        raise HTTPException(status_code=400, detail="text required")
    return await call_microservice(SERVICE_TEXT_ANALYZER, "/analyze/text-deep", {"text": request.username})


@app.post("/url-expander/expand")
async def url_expander_expand(request: GlobalInvestigateRequest):
    """Proxy to url_expander service."""
    target = request.domain or request.email
    if not target:
        raise HTTPException(status_code=400, detail="domain or email required")
    url = f"https://{target}" if not target.startswith(("http://", "https://")) else target
    return await call_microservice(SERVICE_URL_EXPANDER, "/expand/url", {"url": url})


@app.post("/url-expander/preview")
async def url_expander_preview(request: GlobalInvestigateRequest):
    """Proxy to url_expander service with preview."""
    target = request.domain or request.email
    if not target:
        raise HTTPException(status_code=400, detail="domain or email required")
    url = f"https://{target}" if not target.startswith(("http://", "https://")) else target
    return await call_microservice(SERVICE_URL_EXPANDER, "/expand/preview", {"url": url})


@app.post("/shodan-lookup/ip")
async def shodan_lookup_ip(request: GlobalInvestigateRequest):
    """Proxy to shodan_lookup service for IP lookup."""
    if not request.ip:
        raise HTTPException(status_code=400, detail="ip required")
    return await call_microservice(SERVICE_SHODAN_LOOKUP, "/lookup/ip", {"ip": request.ip})


@app.post("/shodan-lookup/domain")
async def shodan_lookup_domain(request: GlobalInvestigateRequest):
    """Proxy to shodan_lookup service for domain resolution + scan."""
    if not request.domain:
        raise HTTPException(status_code=400, detail="domain required")
    return await call_microservice(SERVICE_SHODAN_LOOKUP, "/lookup/domain", {"domain": request.domain})


@app.get("/temp/{filename}")
async def proxy_temp_image(filename: str):
    """Proxy to serve uploaded images from image-search service."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{SERVICE_IMAGE_SEARCH}/temp/{filename}")
            if resp.status_code == 200:
                return StreamingResponse(
                    resp.aiter_bytes(),
                    media_type=resp.headers.get("content-type", "image/jpeg"),
                )
            raise HTTPException(status_code=404, detail="Image not found")
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Image service unreachable")


@app.post("/shodan-lookup/query")
async def shodan_search(request: GlobalInvestigateRequest):
    """Proxy to shodan_lookup service for search query."""
    if not request.username:
        raise HTTPException(status_code=400, detail="username (search query) required")
    return await call_microservice(SERVICE_SHODAN_LOOKUP, "/search/query", {"query": request.username, "max_results": 10})


@app.get("/settings")
async def get_settings():
    """Retourne la configuration générale de la plateforme."""
    from shared.config import get_settings as get_cfg
    cfg = get_cfg()

    # Vérifier l'état des microservices
    services_status = []
    svc_list = [
        ("Gateway", f"http://localhost:8000/health", True),
        ("Breach Lookup", SERVICE_BREACH + "/health", False),
        ("Social Harvester", SERVICE_SOCIAL + "/health", False),
        ("DNS Investigator", SERVICE_DNS + "/health", False),
        ("IP Geolocation", SERVICE_IP + "/health", False),
        ("Person Finder", SERVICE_PERSON_FINDER + "/health", False),
        ("Email Investigator", SERVICE_EMAIL_INVESTIGATOR + "/health", False),
        ("Web Scanner", SERVICE_WEB_SCANNER + "/health", False),
        ("Wayback Machine", SERVICE_WAYBACK_MACHINE + "/health", False),
        ("Image Search", SERVICE_IMAGE_SEARCH + "/health", False),
        ("Phone Analyzer", SERVICE_PHONE_ANALYZER + "/health", False),
        ("Text Analyzer", SERVICE_TEXT_ANALYZER + "/health", False),
        ("URL Expander", SERVICE_URL_EXPANDER + "/health", False),
        ("Shodan Lookup", SERVICE_SHODAN_LOOKUP + "/health", False),
    ]

    for name, url, _ in svc_list:
        try:
            async with httpx.AsyncClient(timeout=2.0) as c:
                resp = await c.get(url)
                services_status.append({
                    "name": name,
                    "status": "online" if resp.status_code == 200 else "degraded",
                    "version": "1.0.0",
                    "port": int(url.split(":")[-1].split("/")[0]),
                })
        except Exception:
            port = int(url.split(":")[-1].split("/")[0]) if ":" in url else 0
            services_status.append({
                "name": name,
                "status": "offline",
                "version": "1.0.0",
                "port": port,
            })

    # Compter les utilisateurs
    user_count = 0
    try:
        from sqlalchemy import func as sqlfunc
        factory = get_async_session()
        async with factory() as session:
            result = await session.execute(sqlfunc.count(User.id))
            user_count = result.scalar() or 0
    except Exception:
        pass

    return {
        "version": "1.0.0",
        "environment": "development",
        "database": {
            "type": "SQLite",
            "driver": "aiosqlite",
        },
        "auth": {
            "method": "JWT + bcrypt",
            "token_expiry": "24 heures",
            "users_count": user_count,
        },
        "services": services_status,
        "api_keys_configured": {
            "shodan": bool(cfg.shodan_api_key),
            "virustotal": bool(cfg.virustotal_api_key),
            "abuseipdb": bool(cfg.abuseipdb_api_key),
            "ipinfo": bool(cfg.ipinfo_api_key),
        },
    }


@app.patch("/settings/password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Change le mot de passe de l'utilisateur connecté."""
    from services.gateway.auth import verify_password, get_password_hash

    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")

    current_user.hashed_password = get_password_hash(request.new_password)
    await session.commit()
    return {"success": True, "message": "Mot de passe modifié avec succès"}


@app.put("/settings/api-keys")
async def update_api_keys(
    request: UpdateApiKeysRequest,
    current_user: User = Depends(get_current_user),
):
    """Met à jour les clés API (stockées en mémoire pour la session)."""
    from shared.config import get_settings as get_cfg
    cfg = get_cfg()

    if request.shodan_api_key:
        cfg.shodan_api_key = request.shodan_api_key
    if request.virustotal_api_key:
        cfg.virustotal_api_key = request.virustotal_api_key
    if request.abuseipdb_api_key:
        cfg.abuseipdb_api_key = request.abuseipdb_api_key
    if request.ipinfo_api_key:
        cfg.ipinfo_api_key = request.ipinfo_api_key
    return {
        "success": True,
        "message": "Clés API mises à jour (pour la session en cours)",
        "configured": {
            "shodan": bool(cfg.shodan_api_key),
            "virustotal": bool(cfg.virustotal_api_key),
            "abuseipdb": bool(cfg.abuseipdb_api_key),
            "ipinfo": bool(cfg.ipinfo_api_key),
        },
    }


# ──────────────────────────────────────────────
# Investigation
# ──────────────────────────────────────────────


@app.post("/investigate/global")
async def investigate_global(
    request: GlobalInvestigateRequest,
    session: AsyncSession = Depends(get_session),
):
    """Perform a full investigation across all microservices in parallel and save a report."""
    tasks = {}

    if request.email:
        tasks["breach_lookup"] = call_microservice(SERVICE_BREACH, "/lookup/email", {"email": request.email})
    if request.username:
        tasks["social_harvester"] = call_microservice(SERVICE_SOCIAL, "/scan/username", {"username": request.username})
    if request.domain:
        tasks["dns_investigator"] = call_microservice(SERVICE_DNS, "/investigate/domain", {"domain": request.domain})
    if request.ip:
        tasks["ip_geoloc"] = call_microservice(SERVICE_IP, "/analyze/ip", {"ip": request.ip})
    if request.username:
        tasks["person_finder"] = call_microservice(SERVICE_PERSON_FINDER, "/search/person", {"name": request.username})

    if not tasks:
        raise HTTPException(
            status_code=400,
            detail="At least one of email, username, domain, or ip must be provided",
        )

    results = await asyncio.gather(*list(tasks.values()), return_exceptions=True)

    service_results = {}
    for i, (name, _) in enumerate(tasks.items()):
        if isinstance(results[i], Exception):
            service_results[name] = {"success": False, "error": str(results[i])}
        else:
            service_results[name] = results[i]

    # Compute aggregate severity/score
    scores = []
    severities = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    max_sev = "info"
    for svc in service_results.values():
        if svc.get("success") and svc.get("data"):
            sev = svc["data"].get("severity", "info")
            sc = svc["data"].get("score", 0)
            scores.append(sc)
            if severities.get(sev, 0) > severities.get(max_sev, 0):
                max_sev = sev

    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Pick the main target for the report
    target = request.email or request.username or request.domain or request.ip

    # Generate a human-readable summary
    summary_lines = []
    for svc_name, svc_data in service_results.items():
        if svc_data.get("success") and svc_data.get("summary"):
            summary_lines.append(f"- {svc_name.replace('_', ' ').title()}: {svc_data['summary']}")
        elif svc_data.get("error"):
            summary_lines.append(f"- {svc_name.replace('_', ' ').title()}: ⚠ {svc_data['error']}")
    summary = "\n".join(summary_lines) if summary_lines else f"Investigation completed on {target}"

    service_names = [s.replace('_', ' ').title() for s in service_results.keys()]
    service_label = ", ".join(service_names)

    # Save report to database
    report = Report(
        target=target,
        service=service_label,
        data={
            "results": {},
        },
        summary=summary,
        severity=max_sev,
        score=round(avg_score, 1),
        raw_output=json.dumps(service_results, indent=2, default=str),
    )

    # Populate data with non-error results (cleaner structure for frontend)
    clean_results = {}
    for svc_name, svc_data in service_results.items():
        if svc_data.get("success") and svc_data.get("data"):
            clean_results[svc_name] = {
                "success": True,
                "summary": svc_data.get("summary", ""),
                "data": svc_data["data"],
            }
        elif svc_data.get("error"):
            clean_results[svc_name] = {
                "success": False,
                "error": svc_data["error"],
            }
    report.data = {
        "target": target,
        "email": request.email,
        "username": request.username,
        "domain": request.domain,
        "ip": request.ip,
        "results": clean_results,
        "overall_severity": max_sev,
        "overall_score": round(avg_score, 1),
        "timestamp": datetime.utcnow().isoformat(),
    }

    try:
        session.add(report)
        await session.commit()
        await session.refresh(report)
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save report: {str(e)}")

    # Prepare response data (same as before + report_id)
    consolidated = report.data.copy()

    return {
        "success": True,
        "report_id": report.id,
        "data": consolidated,
    }


@app.get("/reports")
async def list_reports(
    service: Optional[str] = Query(None),
    target: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """List all reports with optional filtering."""
    try:
        stmt = select(Report).order_by(Report.created_at.desc())

        if service:
            stmt = stmt.where(Report.service == service)
        if target:
            stmt = stmt.where(Report.target.ilike(f"%{target}%"))
        if severity:
            stmt = stmt.where(Report.severity == severity)

        stmt = stmt.offset(offset).limit(limit)
        result = await session.execute(stmt)
        reports = result.scalars().all()

        return {
            "success": True,
            "total": len(reports),
            "offset": offset,
            "limit": limit,
            "reports": [r.to_dict() for r in reports],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")


@app.get("/reports/{report_id}")
async def get_report(report_id: str, session: AsyncSession = Depends(get_session)):
    """Get a single report by ID."""
    try:
        stmt = select(Report).where(Report.id == report_id)
        result = await session.execute(stmt)
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        return {"success": True, "report": report.to_dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get report: {str(e)}")


@app.delete("/reports/{report_id}")
async def delete_report(report_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a report by ID."""
    try:
        stmt = select(Report).where(Report.id == report_id)
        result = await session.execute(stmt)
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        await session.delete(report)
        await session.commit()

        return {"success": True, "message": f"Report {report_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")


@app.get("/reports/{report_id}/export")
async def export_report(
    report_id: str,
    format: str = Query("json", regex="^(json|pdf|markdown)$"),
    session: AsyncSession = Depends(get_session),
):
    """Export a report in JSON or PDF format."""
    try:
        stmt = select(Report).where(Report.id == report_id)
        result = await session.execute(stmt)
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if format == "json":
            content = json.dumps(report.to_dict(), indent=2, default=str)
            return Response(
                content=content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="report_{report_id}.json"',
                },
            )
        elif format == "markdown":
            markdown_content = _build_markdown_report(report)
            return PlainTextResponse(
                content=markdown_content,
                headers={
                    "Content-Disposition": f'attachment; filename="report_{report_id}.md"',
                },
            )
        elif format == "pdf":
            # Generate markdown then use weasyprint for PDF
            markdown_content = _build_markdown_report(report)
            try:
                from weasyprint import HTML
                pdf_bytes = HTML(string=markdown_content).write_pdf()
                return Response(
                    content=pdf_bytes,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f'attachment; filename="report_{report_id}.pdf"',
                    },
                )
            except Exception:
                # Fallback: return as markdown if weasyprint fails
                return PlainTextResponse(
                    content=markdown_content,
                    headers={
                        "Content-Disposition": f'attachment; filename="report_{report_id}.md"',
                    },
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.debug)
