import asyncio
import json
import re
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import init_db, get_session
from shared.models import Report
from shared.http_client import ThothHttpClient

app = FastAPI(
    title="Thoth Breach Lookup Service",
    description="OSINT service that checks emails and usernames against known breaches via public sources (scylla.so, leak-check, built-in database).",
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

KNOWN_BREACHES = [
    {"name": "Collection #1", "date": "2019-01-07", "records": "773M", "domain": "",
     "classes": ["Email", "Password", "Username"], "description": "Mega-collection of 773M unique emails and 21M passwords from multiple sources."},
    {"name": "Collection #2-5", "date": "2019-01-15", "records": "845M", "domain": "",
     "classes": ["Email", "Password", "Username", "IP"], "description": "Follow-up collections adding 845M more records."},
    {"name": "LinkedIn", "date": "2012-05-05", "records": "164M", "domain": "linkedin.com",
     "classes": ["Email", "Password", "Name"], "description": "164M LinkedIn accounts scraped and leaked."},
    {"name": "LinkedIn 2021", "date": "2021-06-22", "records": "700M", "domain": "linkedin.com",
     "classes": ["Email", "Name", "Phone", "Location"], "description": "700M LinkedIn profiles scraped and posted for sale."},
    {"name": "Facebook", "date": "2021-04-03", "records": "533M", "domain": "facebook.com",
     "classes": ["Email", "Phone", "Name", "Location", "DOB"], "description": "533M Facebook accounts scraped via a vulnerability."},
    {"name": "Adobe", "date": "2013-10-04", "records": "153M", "domain": "adobe.com",
     "classes": ["Email", "Password", "Credit Card"], "description": "153M Adobe accounts with encrypted passwords and password hints."},
    {"name": "Dropbox", "date": "2012-07-01", "records": "68M", "domain": "dropbox.com",
     "classes": ["Email", "Password"], "description": "68M Dropbox accounts leaked."},
    {"name": "Twitter", "date": "2022-12-01", "records": "235M", "domain": "twitter.com",
     "classes": ["Email", "Name", "Username"], "description": "235M Twitter accounts scraped and leaked."},
    {"name": "MyFitnessPal", "date": "2018-02-01", "records": "150M", "domain": "myfitnesspal.com",
     "classes": ["Email", "Password", "Username"], "description": "150M MyFitnessPal accounts compromised."},
    {"name": "Canva", "date": "2019-05-24", "records": "139M", "domain": "canva.com",
     "classes": ["Email", "Name", "Password"], "description": "139M Canva accounts including names and passwords."},
    {"name": "Dubsmash", "date": "2019-02-01", "records": "162M", "domain": "dubsmash.com",
     "classes": ["Email", "Password", "Name"], "description": "162M Dubsmash accounts leaked."},
    {"name": "Evite", "date": "2019-04-01", "records": "101M", "domain": "evite.com",
     "classes": ["Email", "Password", "Name", "Phone"], "description": "101M Evite accounts exposed."},
    {"name": "Zynga", "date": "2019-09-24", "records": "218M", "domain": "zynga.com",
     "classes": ["Email", "Password", "Username"], "description": "218M Zynga (Words With Friends) accounts compromised."},
    {"name": "Army.mil", "date": "2009-09-01", "records": "85M", "domain": "army.mil",
     "classes": ["Email", "Password", "Name"], "description": "85M US Army personnel accounts from an unknown breach."},
    {"name": "Antipublic / AntiPublic", "date": "2021-01-01", "records": "458M", "domain": "",
     "classes": ["Email", "Password", "Phone"], "description": "458M records compiled from multiple breaches, shared publicly."},
    {"name": "Exploit.In", "date": "2016-01-01", "records": "593M", "domain": "",
     "classes": ["Email", "Password", "Username"], "description": "593M accounts from exploit.in forum."},
    {"name": "River City Media", "date": "2017-03-01", "records": "1.4B", "domain": "",
     "classes": ["Email", "Name", "IP", "Phone"], "description": "1.4B records from a spam operation, one of the largest leaks."},
    {"name": "Verifications.io", "date": "2019-02-25", "records": "763M", "domain": "verifications.io",
     "classes": ["Email", "Name", "Phone", "IP"], "description": "763M records from an email verification service."},
    {"name": "Data Enrichment", "date": "2019-10-01", "records": "622M", "domain": "",
     "classes": ["Email", "Name", "Phone", "Address"], "description": "622M records from multiple data enrichment companies."},
    {"name": "COMB (Combination)", "date": "2021-02-02", "records": "3.2B", "domain": "",
     "classes": ["Email", "Password"], "description": "3.2B unique email/password pairs from multiple breaches."},
]


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
    sources: list[str] = ["scylla"]

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


def check_known_breaches(email: str) -> list[dict]:
    email_lower = email.lower().strip()
    domain = email_lower.split("@")[1] if "@" in email_lower else ""

    matches = []
    for breach in KNOWN_BREACHES:
        b_domain = breach["domain"].lower()
        if b_domain and (domain == b_domain or domain.endswith("." + b_domain)):
            matches.append({**breach, "matched_by": "domain"})
    return matches


async def search_bing_breach(query: str) -> dict:
    result = {"found": False, "results": [], "count": 0}
    try:
        import httpx as _httpx
        search_query = f"{query} breach leak password exposed"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        async with _httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://www.bing.com/search",
                params={"q": search_query, "count": 10},
                headers=headers,
            )
            if resp.status_code == 200:
                import re as rx
                links = rx.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>', resp.text)
                titles = rx.findall(r'<h2><a[^>]*>(.*?)</a></h2>', resp.text)
                snippets = rx.findall(r'<p[^>]*>(.*?)</p>', resp.text, rx.DOTALL)
                seen = set()
                for i, url in enumerate(links):
                    domain = rx.search(r'https?://([^/]+)', url)
                    domain = domain.group(1) if domain else ""
                    if domain and domain not in seen and not any(skip in url for skip in ['bing.com', 'javascript:', 'msn.com']):
                        seen.add(domain)
                        title = rx.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else ""
                        snippet = rx.sub(r'<[^>]+>', '', snippets[i]).strip()[:300] if i < len(snippets) else ""
                        result["results"].append({"url": url[:300], "domain": domain, "title": title[:150], "snippet": snippet})
                        if len(result["results"]) >= 8:
                            break
                result["found"] = len(result["results"]) > 0
                result["count"] = len(result["results"])
            else:
                result["error"] = f"Bing returned {resp.status_code}"
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


async def search_bing_username(username: str) -> dict:
    result = {"found": False, "results": [], "count": 0}
    try:
        import httpx as _httpx
        search_query = f'"{username}" breach leak password'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        async with _httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://www.bing.com/search",
                params={"q": search_query, "count": 10},
                headers=headers,
            )
            if resp.status_code == 200:
                import re as rx
                links = rx.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>', resp.text)
                titles = rx.findall(r'<h2><a[^>]*>(.*?)</a></h2>', resp.text)
                seen = set()
                for i, url in enumerate(links):
                    domain = rx.search(r'https?://([^/]+)', url)
                    domain = domain.group(1) if domain else ""
                    if domain and domain not in seen and not any(skip in url for skip in ['bing.com', 'javascript:', 'msn.com']):
                        seen.add(domain)
                        title = rx.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else ""
                        result["results"].append({"url": url[:300], "domain": domain, "title": title[:150]})
                        if len(result["results"]) >= 8:
                            break
                result["found"] = len(result["results"]) > 0
                result["count"] = len(result["results"])
    except Exception as e:
        result["error"] = str(e)[:200]
    return result


async def search_leakcheck(email: str) -> dict:
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
        return {"error": str(e)[:200], "found": False}


async def compute_severity(scylla_count: int, known_count: int, leakcheck_count: int = 0) -> tuple[str, float]:
    total = scylla_count + known_count + leakcheck_count
    if total > 5:
        return "critical", 9.0
    elif total > 2:
        return "high", 7.0
    elif total > 0:
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
        "endpoints": ["GET /health", "POST /lookup/email", "POST /lookup/username", "POST /report"],
        "sources": ["web search", "leak-check.net (optionnel)", "built-in breach database (20+ breaches)"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "breach_lookup", "timestamp": datetime.utcnow().isoformat()}


@app.post("/lookup/email")
async def lookup_email(request: EmailLookupRequest):
    try:
        known = check_known_breaches(request.email)
        web = await search_bing_breach(request.email)

        leakcheck = None
        if request.include_leakcheck:
            leakcheck = await search_leakcheck(request.email)

        web_count = web.get("count", 0)
        known_count = len(known)
        leakcheck_count = leakcheck.get("count", 0) if leakcheck else 0
        severity, score = await compute_severity(web_count, known_count, leakcheck_count)

        result = {
            "target": request.email,
            "domain": request.email.split("@")[1],
            "known_breaches": {"match_count": known_count, "matches": known},
            "bing_search": web,
            "leakcheck": leakcheck,
            "breach_count": web_count + known_count + leakcheck_count,
            "severity": severity,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = []
        if web_count > 0:
            parts.append(f"{web_count} résultat(s) web")
        if known_count > 0:
            parts.append(f"{known_count} breach(es) connu(s) sur ce domaine")
        if leakcheck_count > 0:
            parts.append(f"{leakcheck_count} résultat(s) sur leak-check")
        summary = " · ".join(parts) if parts else "Aucun résultat trouvé"

        return {"success": True, "data": result, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lookup failed: {str(e)}")


@app.post("/lookup/username")
async def lookup_username(request: UsernameLookupRequest):
    try:
        bing = await search_bing_username(request.username)
        total_found = 1 if bing.get("found") else 0

        severity, score = "info", 0.0
        if total_found > 1:
            severity, score = "medium", 5.0
        elif total_found > 0:
            severity, score = "low", 2.0

        result = {
            "target": request.username,
            "sources": {"web": bing},
            "total_sources_with_matches": total_found,
            "severity": severity,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        summary = f"Username trouvé dans {total_found} source(s)" if total_found > 0 else "Aucun résultat"
        return {"success": True, "data": result, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Username lookup failed: {str(e)}")


@app.post("/report")
async def save_report(request: ReportSaveRequest, session: AsyncSession = Depends(get_session)):
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
