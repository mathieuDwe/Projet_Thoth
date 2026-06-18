import asyncio
import json
import re
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import init_db, get_session
from shared.models import Report
from shared.http_client import ThothHttpClient

app = FastAPI(
    title="Thoth Breach Lookup Service",
    description="OSINT service that checks email addresses and usernames against known data breaches "
                "using Have I Been Pwned (HIBP) API, leak-check.net, and other public sources.",
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
http_client = ThothHttpClient(service_name="breach_lookup")

# Rate limiting: 1.5s between requests to respect HIBP terms
HIBP_RATE_LIMIT = 1.5


class EmailLookupRequest(BaseModel):
    email: str
    include_leakcheck: bool = False

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v


class UsernameLookupRequest(BaseModel):
    username: str
    sources: list[str] = ["hibp", "scylla"]

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Username must be between 2 and 100 characters")
        if not re.match(r"^[a-zA-Z0-9_.\-]+$", v):
            raise ValueError("Username contains invalid characters")
        return v


class ReportSaveRequest(BaseModel):
    target: str
    service: str = "breach_lookup"
    data: dict = {}
    summary: str = ""
    severity: str = "info"
    score: float = 0.0


async def _hibp_rate_limit():
    """Respect HIBP rate limit (1.5s between requests)."""
    await asyncio.sleep(HIBP_RATE_LIMIT)


async def check_hibp_breaches(email: str) -> dict:
    """Check email against Have I Been Pwned API (v3, no key needed for basic lookup)."""
    result = {"breaches": [], "pastes": [], "count": 0}
    try:
        await _hibp_rate_limit()
        resp = await http_client.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
            headers={"hibp-api-key": settings.virustotal_api_key or ""},
            params={"truncateResponse": "false"},
        )
        if resp.status_code == 200:
            breaches = resp.json()
            result["breaches"] = [
                {
                    "name": b.get("Name"),
                    "domain": b.get("Domain"),
                    "date": b.get("BreachDate"),
                    "classes": b.get("DataClasses", []),
                    "description": (b.get("Description") or "")[:500],
                }
                for b in breaches
            ]
            result["count"] = len(breaches)
        elif resp.status_code == 404:
            result["breaches"] = []
            result["count"] = 0
    except Exception as e:
        result["error_hibp"] = str(e)

    try:
        await _hibp_rate_limit()
        paste_resp = await http_client.get(
            f"https://haveibeenpwned.com/api/v3/pasteaccount/{email}",
            headers={"hibp-api-key": settings.virustotal_api_key or ""},
        )
        if paste_resp.status_code == 200:
            result["pastes"] = paste_resp.json()
    except Exception as e:
        result["error_pastes"] = str(e)

    return result


async def check_leakcheck(email: str) -> dict:
    """Check email against leak-check.net API (if API key configured)."""
    api_key = settings.abuseipdb_api_key
    if not api_key:
        return {"error": "leakcheck_api_key not configured", "found": False}

    try:
        resp = await http_client.get(
            f"https://leak-check.net/api/v1/email/{email}",
            headers={"X-API-Key": api_key},
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "found": data.get("found", False),
                "leaks": data.get("leaks", []),
                "count": len(data.get("leaks", [])),
            }
        return {"error": f"leakcheck returned {resp.status_code}", "found": False}
    except Exception as e:
        return {"error": str(e), "found": False}


async def check_username_hibp(username: str) -> dict:
    """Check username via HIBP (limited support) and public sources."""
    result = {"sources": {}}

    # Check on scylla.so public API (community source)
    try:
        resp = await http_client.get(
            f"https://scylla.so/api/v1/search/{username}",
            params={"type": "username", "limit": 5},
        )
        if resp.status_code == 200:
            data = resp.json()
            result["sources"]["scylla"] = {
                "found": data.get("total", 0) > 0,
                "results": data.get("data", [])[:10],
                "count": data.get("total", 0),
            }
    except Exception as e:
        result["sources"]["scylla"] = {"error": str(e)}

    return result


async def compute_severity(breach_count: int, paste_count: int) -> tuple[str, float]:
    if breach_count > 5:
        return "critical", 9.0
    elif breach_count > 2:
        return "high", 7.0
    elif breach_count > 0 or paste_count > 0:
        return "medium", 4.0
    return "info", 0.0


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/")
async def root():
    return {
        "service": "Thoth Breach Lookup Service",
        "version": "1.0.0",
        "endpoints": [
            "GET /health",
            "POST /lookup/email",
            "POST /lookup/username",
            "POST /report",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "breach_lookup", "timestamp": datetime.utcnow().isoformat()}


@app.post("/lookup/email")
async def lookup_email(request: EmailLookupRequest):
    """Check an email address against known data breaches."""
    try:
        hibp_data = await check_hibp_breaches(request.email)

        leakcheck_data = None
        if request.include_leakcheck:
            leakcheck_data = await check_leakcheck(request.email)

        breach_count = hibp_data.get("count", 0) + (leakcheck_data.get("count", 0) if leakcheck_data else 0)
        paste_count = len(hibp_data.get("pastes", []))
        severity, score = await compute_severity(breach_count, paste_count)

        result = {
            "target": request.email,
            "hibp": hibp_data,
            "leakcheck": leakcheck_data,
            "breach_count": breach_count,
            "paste_count": paste_count,
            "severity": severity,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Build summary
        parts = []
        if breach_count > 0:
            parts.append(f"Found in {breach_count} breach(es)")
        if paste_count > 0:
            parts.append(f"Found in {paste_count} paste(s)")
        summary = "; ".join(parts) if parts else "No breaches found"

        return {"success": True, "data": result, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lookup failed: {str(e)}")


@app.post("/lookup/username")
async def lookup_username(request: UsernameLookupRequest):
    """Check a username against public breach sources."""
    try:
        results = await check_username_hibp(request.username)

        total_found = sum(
            1 for s in results.get("sources", {}).values()
            if isinstance(s, dict) and s.get("found")
        )
        severity = "info"
        score = 0.0
        if total_found > 1:
            severity, score = "medium", 5.0
        elif total_found > 0:
            severity, score = "low", 2.0

        result = {
            "target": request.username,
            "sources": results["sources"],
            "total_sources_with_matches": total_found,
            "severity": severity,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        summary = f"Username found in {total_found} source(s)" if total_found > 0 else "Username not found in any source"

        return {"success": True, "data": result, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Username lookup failed: {str(e)}")


@app.post("/report")
async def save_report(request: ReportSaveRequest, session: AsyncSession = Depends(get_session)):
    """Save a breach lookup report to the database."""
    try:
        report = Report(
            target=request.target,
            service=request.service,
            data=request.data,
            summary=request.summary,
            severity=request.severity,
            score=request.score,
            raw_output=json.dumps(request.data, indent=2, default=str),
        )
        session.add(report)
        await session.commit()
        await session.refresh(report)
        return {"success": True, "report_id": report.id}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save report: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=settings.debug)
