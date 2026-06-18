import asyncio
import json
import re
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import init_db, get_session
from shared.models import Report
from shared.http_client import ThothHttpClient

app = FastAPI(
    title="Thoth Social Harvester Service",
    description="OSINT service that scans usernames and emails across social media platforms "
                "(GitHub, Reddit, Twitter/X, Instagram, Telegram) to discover digital footprints.",
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
http_client = ThothHttpClient(service_name="social_harvester")

# Platform check configuration: endpoint, expected indicator of existence
PLATFORMS_USERNAME = {
    "github": {
        "url": "https://github.com/{username}",
        "exists_indicator": 200,
        "type": "profile",
    },
    "reddit": {
        "url": "https://www.reddit.com/user/{username}",
        "exists_indicator": 200,
        "type": "profile",
    },
    "twitter": {
        "url": "https://twitter.com/{username}",
        "exists_indicator": 200,
        "type": "profile",
    },
    "instagram": {
        "url": "https://www.instagram.com/{username}/",
        "exists_indicator": 200,
        "type": "profile",
    },
    "telegram": {
        "url": "https://t.me/{username}",
        "exists_indicator": 200,
        "type": "profile",
    },
}

PLATFORMS_EMAIL = {
    "gravatar": {
        "url": "https://www.gravatar.com/avatar/{hash}?d=404",
        "type": "avatar",
    },
}


class UsernameScanRequest(BaseModel):
    username: str
    platforms: list[str] = list(PLATFORMS_USERNAME.keys())

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 50:
            raise ValueError("Username must be between 2 and 50 characters")
        if not re.match(r"^[a-zA-Z0-9_.\-]+$", v):
            raise ValueError("Username contains invalid characters")
        return v

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: list[str]) -> list[str]:
        valid = set(PLATFORMS_USERNAME.keys())
        for p in v:
            if p not in valid:
                raise ValueError(f"Invalid platform: {p}. Valid: {', '.join(sorted(valid))}")
        return v


class EmailScanRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v


class ReportSaveRequest(BaseModel):
    target: str
    service: str = "social_harvester"
    data: dict = {}
    summary: str = ""
    severity: str = "info"
    score: float = 0.0


async def check_platform_username(username: str, platform: str, config: dict) -> dict:
    """Check if a username exists on a single platform with isolated timeout."""
    url = config["url"].format(username=username)
    result = {
        "platform": platform,
        "url": url,
        "exists": False,
        "status_code": None,
        "error": None,
    }
    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ThothOSINT/1.0)"},
        ) as client:
            resp = await client.get(url)
            result["status_code"] = resp.status_code

            if resp.status_code == 200:
                result["exists"] = True
            elif resp.status_code == 404:
                result["exists"] = False
            elif resp.status_code == 429:
                result["error"] = "rate_limited"
            elif resp.status_code == 403:
                result["error"] = "blocked"
            else:
                result["exists"] = resp.status_code not in (404, 410)
    except httpx.TimeoutException:
        result["error"] = "timeout"
    except httpx.ConnectError:
        result["error"] = "connection_error"
    except Exception as e:
        result["error"] = str(e)[:100]

    return result


async def check_email_platforms(email: str) -> list[dict]:
    """Check email against email-associated platforms."""
    import hashlib
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    results = []

    # Gravatar check
    gravatar_url = PLATFORMS_EMAIL["gravatar"]["url"].format(hash=email_hash)
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            resp = await client.get(gravatar_url)
            if resp.status_code == 200:
                results.append({
                    "platform": "gravatar",
                    "url": f"https://www.gravatar.com/{email_hash}",
                    "exists": True,
                    "type": "avatar",
                })
            else:
                results.append({
                    "platform": "gravatar",
                    "exists": False,
                })
    except Exception as e:
        results.append({"platform": "gravatar", "error": str(e)[:100]})

    return results


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/")
async def root():
    return {
        "service": "Thoth Social Harvester Service",
        "version": "1.0.0",
        "endpoints": [
            "GET /health",
            "POST /scan/username",
            "POST /scan/email",
            "POST /report",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "social_harvester", "timestamp": datetime.utcnow().isoformat()}


@app.post("/scan/username")
async def scan_username(request: UsernameScanRequest):
    """Scan a username across configured social media platforms."""
    try:
        tasks = []
        platforms_to_check = [p for p in request.platforms if p in PLATFORMS_USERNAME]
        for platform in platforms_to_check:
            config = PLATFORMS_USERNAME[platform]
            tasks.append(check_platform_username(request.username, platform, config))

        platform_results = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for r in platform_results:
            if isinstance(r, Exception):
                results.append({"error": str(r)})
            else:
                results.append(r)

        found_count = sum(1 for r in results if isinstance(r, dict) and r.get("exists"))
        total_checked = len(results)

        severity = "info"
        score = 0.0
        if found_count >= 4:
            severity, score = "high", 7.0
        elif found_count >= 2:
            severity, score = "medium", 4.0
        elif found_count >= 1:
            severity, score = "low", 2.0

        result_data = {
            "target": request.username,
            "platforms": results,
            "found_count": found_count,
            "total_checked": total_checked,
            "severity": severity,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        summary = f"Username '{request.username}' found on {found_count}/{total_checked} platforms"

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Username scan failed: {str(e)}")


@app.post("/scan/email")
async def scan_email(request: EmailScanRequest):
    """Scan an email address across email-associated platforms."""
    try:
        platform_results = await check_email_platforms(request.email)

        found_count = sum(1 for r in platform_results if r.get("exists"))

        result_data = {
            "target": request.email,
            "platforms": platform_results,
            "found_count": found_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

        summary = f"Email '{request.email}' found on {found_count} platform(s)" if found_count else "No platforms found for email"

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email scan failed: {str(e)}")


@app.post("/report")
async def save_report(request: ReportSaveRequest, session: AsyncSession = Depends(get_session)):
    """Save a social harvest report to the database."""
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
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=settings.debug)
