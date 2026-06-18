import asyncio
import hashlib
import json
import re
from datetime import datetime
from typing import Optional

import dns.resolver
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from shared.config import get_settings
from shared.http_client import ThothHttpClient

app = FastAPI(
    title="Thoth Email Investigator Service",
    description="OSINT service that analyzes email addresses: validates format, checks MX records, "
                "finds Gravatar profiles, and assesses email security configuration.",
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
http_client = ThothHttpClient(service_name="email_investigator")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
DNS_NAMESERVERS = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
COMMON_PROVIDERS = {
    "gmail.com": "Google Gmail",
    "yahoo.com": "Yahoo Mail",
    "yahoo.fr": "Yahoo Mail",
    "outlook.com": "Microsoft Outlook",
    "hotmail.com": "Microsoft Hotmail",
    "live.com": "Microsoft Live",
    "msn.com": "MSN",
    "icloud.com": "Apple iCloud",
    "me.com": "Apple Me",
    "protonmail.com": "ProtonMail",
    "proton.me": "ProtonMail",
    "mail.com": "Mail.com",
    "gmx.com": "GMX",
    "gmx.fr": "GMX",
    "yandex.com": "Yandex",
    "yandex.ru": "Yandex",
    "aol.com": "AOL",
    "zoho.com": "Zoho Mail",
    "fastmail.com": "FastMail",
    "tutanota.com": "Tutanota",
    "tuta.io": "Tuta",
    "disroot.org": "Disroot",
    "riseup.net": "Riseup",
}


class EmailAnalyzeRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        if len(v) > 254:
            raise ValueError("Email too long")
        return v


class DomainMxRequest(BaseModel):
    domain: str

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid domain format")
        return v


async def check_mx_records(domain: str) -> list[dict]:
    results = []
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = DNS_NAMESERVERS
        resolver.timeout = 5.0
        resolver.lifetime = 5.0
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(resolver.resolve(domain, "MX"))
        )
        for answer in answers:
            results.append({
                "preference": answer.preference,
                "exchange": str(answer.exchange),
            })
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
        pass
    except Exception as e:
        results.append({"error": str(e)[:100]})
    return results


async def check_gravatar(email: str) -> dict:
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    gravatar_url = f"https://www.gravatar.com/avatar/{email_hash}"
    result = {"hash": email_hash, "profile_url": f"https://www.gravatar.com/{email_hash}", "has_avatar": False}
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
            resp = await client.get(f"{gravatar_url}?d=404")
            if resp.status_code == 200:
                result["has_avatar"] = True
                result["avatar_url"] = f"{gravatar_url}?s=256"
    except Exception:
        pass
    return result


def generate_social_handles(email: str) -> list[dict]:
    local_part = email.split("@")[0]
    handles = []
    suggestions = [
        (local_part, "local_part"),
        (local_part.replace(".", ""), "no_dots"),
        (local_part.replace("_", ""), "no_underscores"),
        (local_part.replace("-", ""), "no_hyphens"),
        (local_part.split("+")[0], "before_plus"),
    ]
    seen = set()
    for handle, method in suggestions:
        if handle and len(handle) >= 3 and handle not in seen:
            seen.add(handle)
            handles.append({"handle": handle, "method": method})
    return handles


def assess_email_risk(has_mx: bool, has_gravatar: bool, provider: Optional[str]) -> tuple[str, float]:
    score = 0.0
    if not has_mx:
        score += 3.0
    if has_gravatar:
        score += 1.5
    if provider:
        score -= 0.5
    score = max(0, min(score, 10))
    if score >= 5:
        return "medium", score
    return "info", score


@app.on_event("startup")
async def startup():
    pass


@app.get("/")
async def root():
    return {
        "service": "Thoth Email Investigator Service",
        "version": "1.0.0",
        "endpoints": ["GET /health", "POST /analyze/email", "POST /analyze/domain-mx"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "email_investigator", "timestamp": datetime.utcnow().isoformat()}


@app.post("/analyze/email")
async def analyze_email(request: EmailAnalyzeRequest):
    try:
        email = request.email
        local_part, domain = email.split("@")

        mx_task = check_mx_records(domain)
        gravatar_task = check_gravatar(email)
        mx_records, gravatar = await asyncio.gather(mx_task, gravatar_task, return_exceptions=True)

        if isinstance(mx_records, Exception):
            mx_records = []
        if isinstance(gravatar, Exception):
            gravatar = {"has_avatar": False, "hash": ""}

        has_mx = len(mx_records) > 0 and "error" not in mx_records[0] if mx_records else False
        provider = COMMON_PROVIDERS.get(domain, None)
        handles = generate_social_handles(email)
        severity, score = assess_email_risk(has_mx, gravatar.get("has_avatar", False), provider)

        result_data = {
            "target": email,
            "local_part": local_part,
            "domain": domain,
            "provider": provider,
            "has_mx_records": has_mx,
            "mx_records": mx_records,
            "gravatar": gravatar,
            "social_handles": handles,
            "severity": severity,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = []
        if provider:
            parts.append(f"Provider: {provider}")
        if has_mx:
            parts.append(f"{len(mx_records)} MX server(s)")
        else:
            parts.append("No MX records (suspicious)")
        if gravatar.get("has_avatar"):
            parts.append("Gravatar found")
        parts.append(f"{len(handles)} possible social handle(s)")
        summary = "; ".join(parts)

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email analysis failed: {str(e)}")


@app.post("/analyze/domain-mx")
async def analyze_domain_mx(request: DomainMxRequest):
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = DNS_NAMESERVERS
        resolver.timeout = 5.0
        resolver.lifetime = 5.0

        async def resolve_txt(record: str):
            try:
                answers = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: list(resolver.resolve(record, "TXT"))
                )
                return [str(a) for a in answers]
            except Exception:
                return []

        mx_task = check_mx_records(request.domain)
        spf_task = resolve_txt(request.domain)
        dmarc_task = resolve_txt(f"_dmarc.{request.domain}")
        dkim_task = resolve_txt(f"default._domainkey.{request.domain}")

        mx_records, spf, dmarc, dkim = await asyncio.gather(mx_task, spf_task, dmarc_task, dkim_task, return_exceptions=True)

        if isinstance(mx_records, Exception):
            mx_records = []
        if isinstance(spf, Exception):
            spf = []
        if isinstance(dmarc, Exception):
            dmarc = []
        if isinstance(dkim, Exception):
            dkim = []

        spf_record = next((r for r in spf if r.startswith("v=spf1")), None)
        dmarc_record = next((r for r in dmarc if r.startswith("v=DMARC1")), None)
        dkim_record = next((r for r in dkim if r.startswith("v=DKIM1")), None)

        result_data = {
            "target": request.domain,
            "mx_records": mx_records,
            "mx_count": len(mx_records),
            "spf": spf_record,
            "dkim": dkim_record,
            "dmarc": dmarc_record,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = [f"{len(mx_records)} MX server(s)"]
        if spf_record:
            parts.append("SPF configured")
        if dkim_record:
            parts.append("DKIM configured")
        if dmarc_record:
            parts.append("DMARC configured")
        summary = "; ".join(parts)

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Domain MX analysis failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006, reload=settings.debug)
