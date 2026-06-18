import asyncio
import json
import os
from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
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
        ],
        "microservices": {
            "breach_lookup": f"{SERVICE_BREACH}/health",
            "social_harvester": f"{SERVICE_SOCIAL}/health",
            "dns_investigator": f"{SERVICE_DNS}/health",
            "ip_geoloc": f"{SERVICE_IP}/health",
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
    for svc_url in [SERVICE_BREACH, SERVICE_SOCIAL, SERVICE_DNS, SERVICE_IP]:
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
    ]

    service_urls = {
        "DNS Investigator": SERVICE_DNS,
        "Breach Lookup": SERVICE_BREACH,
        "Social Harvester": SERVICE_SOCIAL,
        "IP Geolocation": SERVICE_IP,
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
