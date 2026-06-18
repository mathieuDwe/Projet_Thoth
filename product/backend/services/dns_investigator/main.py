import asyncio
import json
import re
from datetime import datetime
from typing import Optional

import dns.resolver
import dns.exception
import dns.rdatatype
import whois
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import get_settings
from shared.database import init_db, get_session
from shared.models import Report
from shared.http_client import ThothHttpClient

app = FastAPI(
    title="Thoth DNS Investigator Service",
    description="OSINT service that performs deep DNS reconnaissance including record enumeration, "
                "subdomain discovery via crt.sh, WHOIS lookups, and email security configuration "
                "(SPF, DKIM, DMARC) analysis.",
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
http_client = ThothHttpClient(service_name="dns_investigator")

# DNS record types to query
DNS_RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "SRV", "CAA"]

# Default DNS resolvers fallback
DNS_NAMESERVERS = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]


class DomainInvestigateRequest(BaseModel):
    domain: str
    include_subdomains: bool = True
    include_whois: bool = True
    include_dnssec: bool = False

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid domain format")
        return v


class ReportSaveRequest(BaseModel):
    target: str
    service: str = "dns_investigator"
    data: dict = {}
    summary: str = ""
    severity: str = "info"
    score: float = 0.0


async def resolve_dns_records(domain: str) -> dict:
    """Resolve DNS records for the domain using dnspython."""
    resolver = dns.resolver.Resolver()
    resolver.nameservers = DNS_NAMESERVERS
    resolver.timeout = 5.0
    resolver.lifetime = 5.0

    records = {}

    for rtype in DNS_RECORD_TYPES:
        try:
            answers = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda rt=rtype: list(resolver.resolve(domain, rt)),
            )
            rdata_list = []
            for answer in answers:
                if rtype in ("MX",):
                    rdata_list.append({
                        "preference": answer.preference,
                        "exchange": str(answer.exchange),
                    })
                elif rtype in ("SOA",):
                    rdata_list.append({
                        "mname": str(answer.mname),
                        "rname": str(answer.rname),
                        "serial": answer.serial,
                        "refresh": answer.refresh,
                        "retry": answer.retry,
                        "expire": answer.expire,
                        "minimum": answer.minimum,
                    })
                elif rtype in ("SRV",):
                    rdata_list.append({
                        "priority": answer.priority,
                        "weight": answer.weight,
                        "port": answer.port,
                        "target": str(answer.target),
                    })
                elif rtype in ("CAA",):
                    rdata_list.append({
                        "flags": answer.flags,
                        "tag": answer.tag,
                        "value": answer.value,
                    })
                else:
                    rdata_list.append(str(answer))
            if rdata_list:
                records[rtype] = rdata_list
        except dns.resolver.NoAnswer:
            records[rtype] = []
        except dns.resolver.NXDOMAIN:
            records["error"] = "NXDOMAIN - Domain does not exist"
            break
        except dns.exception.Timeout:
            records[rtype] = ["timeout"]
        except Exception as e:
            records[rtype] = [f"error: {str(e)[:100]}"]

    return records


async def discover_subdomains(domain: str) -> dict:
    """Discover subdomains via crt.sh Certificate Transparency logs."""
    result = {"subdomains": [], "count": 0}
    try:
        resp = await http_client.get(
            f"https://crt.sh/?q=%25.{domain}&output=json",
            headers={"Accept": "application/json"},
        )
        if resp.status_code == 200:
            entries = resp.json()
            unique_subdomains = set()
            for entry in entries:
                name = entry.get("name_value", "")
                for sub in name.split("\n"):
                    sub = sub.strip().lower()
                    if sub.endswith(f".{domain}") and sub != f"*.{domain}":
                        unique_subdomains.add(sub)
            result["subdomains"] = sorted(unique_subdomains)[:100]
            result["count"] = len(result["subdomains"])
    except Exception as e:
        result["error"] = str(e)[:200]

    return result


async def lookup_whois(domain: str) -> dict:
    """Perform WHOIS lookup for the domain."""
    result = {}
    try:
        w = await asyncio.get_event_loop().run_in_executor(
            None, lambda: whois.whois(domain)
        )
        for key in ("domain_name", "registrar", "whois_server", "creation_date",
                     "expiration_date", "updated_date", "name_servers", "status",
                     "emails", "org", "country", "state", "city", "address"):
            val = getattr(w, key, None)
            if val:
                if isinstance(val, list):
                    result[key] = [str(v) for v in val]
                elif isinstance(val, datetime):
                    result[key] = val.isoformat()
                else:
                    result[key] = str(val)
    except Exception as e:
        result["error"] = str(e)[:200]

    return result


async def check_email_security(domain: str) -> dict:
    """Check SPF, DKIM, and DMARC security records."""
    resolver = dns.resolver.Resolver()
    resolver.nameservers = DNS_NAMESERVERS
    resolver.timeout = 5.0
    resolver.lifetime = 5.0

    security = {"spf": None, "dkim": None, "dmarc": None}

    # SPF check via TXT records
    try:
        txt_records = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(resolver.resolve(domain, "TXT"))
        )
        for txt in txt_records:
            txt_str = str(txt)
            if txt_str.startswith("v=spf1"):
                security["spf"] = txt_str
                break
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
        security["spf"] = "not_found"

    # DKIM check (common selector: google, default, mail)
    dkim_selectors = ["google", "default", "mail", "selector1", "selector2"]
    for selector in dkim_selectors:
        try:
            dkim_record = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda s=selector: list(resolver.resolve(f"{s}._domainkey.{domain}", "TXT")),
            )
            if dkim_record:
                security["dkim"] = {
                    "selector": selector,
                    "value": str(dkim_record[0]),
                }
                break
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
            continue

    # DMARC check
    try:
        dmarc_records = await asyncio.get_event_loop().run_in_executor(
            None, lambda: list(resolver.resolve(f"_dmarc.{domain}", "TXT"))
        )
        if dmarc_records:
            security["dmarc"] = str(dmarc_records[0])
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
        security["dmarc"] = "not_found"

    return security


def compute_severity(dns_records: dict, whois_data: dict) -> tuple[str, float]:
    issues = 0

    # Missing basic records
    if "MX" in dns_records and not dns_records["MX"]:
        issues += 1
    if "error" in dns_records:
        issues += 3

    score = min(issues * 2.0, 10.0)
    if score >= 7:
        return "high", score
    elif score >= 3:
        return "medium", score
    return "info", max(score, 0.0)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/")
async def root():
    return {
        "service": "Thoth DNS Investigator Service",
        "version": "1.0.0",
        "endpoints": [
            "GET /health",
            "POST /investigate/domain",
            "POST /report",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "dns_investigator", "timestamp": datetime.utcnow().isoformat()}


@app.post("/investigate/domain")
async def investigate_domain(request: DomainInvestigateRequest):
    """Perform full DNS investigation on a domain."""
    try:
        # Run DNS resolution in parallel with other tasks
        dns_task = resolve_dns_records(request.domain)
        subdomain_task = discover_subdomains(request.domain) if request.include_subdomains else None
        whois_task = lookup_whois(request.domain) if request.include_whois else None
        email_task = check_email_security(request.domain)

        tasks = [dns_task, email_task]
        if subdomain_task:
            tasks.append(subdomain_task)
        if whois_task:
            tasks.append(whois_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        dns_records = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
        email_security = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])}
        subdomains = results[2] if len(results) > 2 and not isinstance(results[2], Exception) else {"count": 0, "subdomains": []}
        whois_data = results[3] if len(results) > 3 and not isinstance(results[3], Exception) else {}

        severity, score = compute_severity(dns_records, whois_data)

        result_data = {
            "target": request.domain,
            "dns_records": dns_records,
            "email_security": email_security,
            "subdomains": subdomains,
            "whois": whois_data,
            "severity": severity,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Build summary
        parts = []
        record_count = sum(1 for v in dns_records.values() if isinstance(v, list) and len(v) > 0)
        parts.append(f"{record_count} record types resolved")
        if subdomains.get("count", 0) > 0:
            parts.append(f"{subdomains['count']} subdomains discovered")
        if whois_data and "error" not in whois_data:
            parts.append("WHOIS data found")
        if email_security.get("spf") and email_security["spf"] != "not_found":
            parts.append("SPF configured")
        if email_security.get("dkim"):
            parts.append("DKIM configured")
        if email_security.get("dmarc") and email_security["dmarc"] != "not_found":
            parts.append("DMARC configured")

        summary = "; ".join(parts) if parts else "Basic DNS data collected"

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Domain investigation failed: {str(e)}")


@app.post("/report")
async def save_report(request: ReportSaveRequest, session: AsyncSession = Depends(get_session)):
    """Save a DNS investigation report to the database."""
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
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=settings.debug)
