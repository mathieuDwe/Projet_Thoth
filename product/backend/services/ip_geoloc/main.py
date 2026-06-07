import asyncio
import ipaddress
import json
import socket
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
    title="Thoth IP Geolocation Service",
    description="OSINT service that analyzes IP addresses for geolocation, VPN/proxy detection, "
                "ASN information, reverse DNS, and optional port scanning.",
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
http_client = ThothHttpClient(service_name="ip_geoloc")

# Common ports to scan (optional)
COMMON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995,
    1433, 1521, 2049, 3306, 3389, 5432, 5900, 5985, 5986, 6379, 8080, 8443, 9090, 27017,
]


class IPAnalyzeRequest(BaseModel):
    ip: str
    scan_ports: bool = False

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        v = v.strip()
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("Invalid IP address format")
        return v


class BulkIPAnalyzeRequest(BaseModel):
    ips: list[str]
    scan_ports: bool = False

    @field_validator("ips")
    @classmethod
    def validate_ips(cls, v: list[str]) -> list[str]:
        validated = []
        for ip in v:
            try:
                ipaddress.ip_address(ip.strip())
                validated.append(ip.strip())
            except ValueError:
                raise ValueError(f"Invalid IP address: {ip}")
        if len(validated) > 50:
            raise ValueError("Maximum 50 IPs per bulk request")
        return validated


class ReportSaveRequest(BaseModel):
    target: str
    service: str = "ip_geoloc"
    data: dict = {}
    summary: str = ""
    severity: str = "info"
    score: float = 0.0


async def geolocate_ip(ip: str) -> dict:
    """Geolocate IP using ip-api.com (free, no key required, 45 req/min limit)."""
    result = {}
    try:
        resp = await http_client.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,message,continent,continentCode,country,countryCode,"
                              "region,regionName,city,district,zip,lat,lon,timezone,offset,"
                              "currency,isp,org,as,asname,reverse,mobile,proxy,hosting,query"},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                result = {
                    "continent": data.get("continent"),
                    "continent_code": data.get("continentCode"),
                    "country": data.get("country"),
                    "country_code": data.get("countryCode"),
                    "region": data.get("regionName"),
                    "city": data.get("city"),
                    "district": data.get("district"),
                    "zip": data.get("zip"),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "timezone": data.get("timezone"),
                    "isp": data.get("isp"),
                    "org": data.get("org"),
                    "as": data.get("as"),
                    "asname": data.get("asname"),
                    "mobile": data.get("mobile", False),
                    "proxy": data.get("proxy", False),
                    "hosting": data.get("hosting", False),
                    "reverse_dns": data.get("reverse"),
                }
            else:
                result["error"] = data.get("message", "Unknown API error")
        else:
            result["error"] = f"ip-api.com returned {resp.status_code}"
    except Exception as e:
        result["error"] = str(e)[:200]

    return result


async def reverse_dns_lookup(ip: str) -> Optional[str]:
    """Perform reverse DNS lookup."""
    try:
        hostname = await asyncio.get_event_loop().run_in_executor(
            None, lambda: socket.gethostbyaddr(ip)
        )
        return hostname[0] if hostname else None
    except (socket.herror, socket.gaierror, OSError):
        return None


async def check_vpn_databases(ip: str, geo_data: dict) -> dict:
    """Aggregate VPN/proxy detection signals."""
    vpn_result = {
        "ip_api_proxy": geo_data.get("proxy", False),
        "ip_api_hosting": geo_data.get("hosting", False),
        "ip_api_mobile": geo_data.get("mobile", False),
        "vpn_detected": False,
        "risk": "low",
    }

    # Determine VPN risk
    signals = 0
    if vpn_result["ip_api_proxy"]:
        signals += 1
    if vpn_result["ip_api_hosting"]:
        signals += 1

    if signals >= 2:
        vpn_result["vpn_detected"] = True
        vpn_result["risk"] = "high"
    elif signals == 1:
        vpn_result["vpn_detected"] = True
        vpn_result["risk"] = "medium"

    return vpn_result


async def scan_ports(ip: str, ports: list[int]) -> list[dict]:
    """Scan common ports for the given IP using TCP connect."""
    open_ports = []

    async def check_port(port: int) -> Optional[dict]:
        try:
            conn = asyncio.open_connection(ip, port)
            _, writer = await asyncio.wait_for(conn, timeout=2.0)
            writer.close()
            await writer.wait_closed()
            service = _get_common_service(port)
            return {"port": port, "state": "open", "service": service}
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return None

    tasks = [check_port(port) for port in ports]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for result in completed:
        if isinstance(result, dict):
            open_ports.append(result)

    return sorted(open_ports, key=lambda x: x["port"])


def _get_common_service(port: int) -> str:
    services = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 111: "RPC", 135: "MSRPC", 139: "NetBIOS",
        143: "IMAP", 443: "HTTPS", 445: "SMB", 993: "IMAPS", 995: "POP3S",
        1433: "MSSQL", 1521: "Oracle", 2049: "NFS", 3306: "MySQL",
        3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 5985: "WinRM-HTTP",
        5986: "WinRM-HTTPS", 6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
        9090: "HTTP-Alt2", 27017: "MongoDB",
    }
    return services.get(port, "Unknown")


def compute_severity(geo_data: dict, vpn_data: dict, open_ports: list) -> tuple[str, float]:
    score = 0.0

    if vpn_data.get("risk") == "high":
        score += 4.0
    elif vpn_data.get("risk") == "medium":
        score += 2.0

    sensitive_ports = {22, 3389, 23, 445, 3306, 5432, 27017, 1433}
    sensitive_open = [p for p in open_ports if p["port"] in sensitive_ports]
    score += len(sensitive_open) * 2.0
    score += len(open_ports) * 0.5

    if "error" in geo_data:
        score += 1.0

    score = min(score, 10.0)
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
        "service": "Thoth IP Geolocation Service",
        "version": "1.0.0",
        "endpoints": [
            "GET /health",
            "POST /analyze/ip",
            "POST /analyze/bulk",
            "POST /report",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ip_geoloc", "timestamp": datetime.utcnow().isoformat()}


@app.post("/analyze/ip")
async def analyze_ip(request: IPAnalyzeRequest):
    """Perform comprehensive IP analysis."""
    try:
        geo_data = await geolocate_ip(request.ip)

        rdns = await reverse_dns_lookup(request.ip)
        if rdns:
            geo_data["reverse_dns_name"] = rdns

        vpn_data = await check_vpn_databases(request.ip, geo_data)

        open_ports = []
        if request.scan_ports:
            open_ports = await scan_ports(request.ip, COMMON_PORTS)

        severity, score = compute_severity(geo_data, vpn_data, open_ports)

        result_data = {
            "target": request.ip,
            "geolocation": geo_data,
            "vpn_proxy_analysis": vpn_data,
            "ports": open_ports if request.scan_ports else None,
            "port_scan_enabled": request.scan_ports,
            "severity": severity,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = []
        if "country" in geo_data:
            parts.append(f"Located in {geo_data['country']}")
        if vpn_data.get("vpn_detected"):
            parts.append(f"VPN/Proxy detected (risk: {vpn_data['risk']})")
        if open_ports:
            parts.append(f"{len(open_ports)} open port(s) found")
        if rdns:
            parts.append(f"PTR: {rdns}")

        summary = "; ".join(parts) if parts else "Basic IP data collected"

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IP analysis failed: {str(e)}")


@app.post("/analyze/bulk")
async def analyze_bulk(request: BulkIPAnalyzeRequest):
    """Analyze multiple IP addresses in parallel."""
    try:
        tasks = []
        for ip in request.ips:
            tasks.append(analyze_ip(IPAnalyzeRequest(ip=ip, scan_ports=request.scan_ports)))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        analyses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                analyses.append({
                    "ip": request.ips[i],
                    "success": False,
                    "error": str(result),
                })
            else:
                analyses.append({
                    "ip": request.ips[i],
                    "success": True,
                    "data": result.get("data"),
                    "summary": result.get("summary"),
                })

        high_risk = sum(1 for a in analyses if a.get("data", {}).get("severity") == "high")

        result_data = {
            "total": len(request.ips),
            "high_risk_count": high_risk,
            "analyses": analyses,
            "timestamp": datetime.utcnow().isoformat(),
        }

        summary = f"Analyzed {len(request.ips)} IP(s), {high_risk} flagged as high risk"

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk analysis failed: {str(e)}")


@app.post("/report")
async def save_report(request: ReportSaveRequest, session: AsyncSession = Depends(get_session)):
    """Save an IP geolocation report to the database."""
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
    uvicorn.run(app, host="0.0.0.0", port=8004, reload=settings.debug)
