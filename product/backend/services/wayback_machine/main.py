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
    title="Thoth Wayback Machine Service",
    description="OSINT service that queries the Internet Archive Wayback Machine to discover "
                "historical snapshots of websites and URLs.",
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
http_client = ThothHttpClient(service_name="wayback_machine")

USER_AGENT = "Mozilla/5.0 (compatible; ThothOSINT/1.0)"

CDX_API = "https://web.archive.org/cdx/search/cdx"
AVAILABILITY_API = "https://archive.org/wayback/available"


class WaybackRequest(BaseModel):
    url: str
    max_results: int = 20

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("URL too long")
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be between 1 and 100")
        return v


class UrlAvailableRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class RecentSnapshotsRequest(BaseModel):
    url: str
    max_results: int = 10

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


async def query_cdx(url: str, max_results: int, from_date: str = "", to_date: str = "") -> list[dict]:
    results = []
    try:
        params = {
            "url": url,
            "output": "json",
            "limit": max_results,
            "fl": "timestamp,original,statuscode,mimetype,length",
        }
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(CDX_API, params=params, headers={"User-Agent": USER_AGENT})
            if resp.status_code == 200:
                data = resp.json()
                for row in data[1:]:
                    if len(row) >= 5:
                        timestamp = row[0]
                        formatted = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]} {timestamp[8:10]}:{timestamp[10:12]}:{timestamp[12:14]}"
                        results.append({
                            "timestamp": timestamp,
                            "date": formatted,
                            "original_url": row[1],
                            "status_code": row[2],
                            "mime_type": row[3],
                            "length": row[4],
                            "archive_url": f"https://web.archive.org/web/{timestamp}/{row[1]}",
                        })
    except Exception:
        pass
    return results


@app.on_event("startup")
async def startup():
    pass


@app.get("/")
async def root():
    return {
        "service": "Thoth Wayback Machine Service",
        "version": "1.0.0",
        "endpoints": ["GET /health", "POST /archive/snapshots", "POST /archive/available", "POST /archive/recent"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "wayback_machine", "timestamp": datetime.utcnow().isoformat()}


@app.post("/archive/snapshots")
async def get_snapshots(request: WaybackRequest):
    try:
        snapshots = await query_cdx(request.url, request.max_results)
        result_data = {
            "target": request.url,
            "total": len(snapshots),
            "snapshots": snapshots,
            "timestamp": datetime.utcnow().isoformat(),
        }
        summary = f"{len(snapshots)} snapshot(s) found for {request.url}" if snapshots else "No snapshots found"
        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Snapshot query failed: {str(e)}")


@app.post("/archive/available")
async def check_available(request: UrlAvailableRequest):
    try:
        result = {"target": request.url, "available": False, "closest_snapshot": None}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                AVAILABILITY_API,
                params={"url": request.url},
                headers={"User-Agent": USER_AGENT},
            )
            if resp.status_code == 200:
                data = resp.json()
                snapshots = data.get("archived_snapshots", {})
                closest = snapshots.get("closest", {})
                if closest:
                    result["available"] = True
                    result["closest_snapshot"] = {
                        "timestamp": closest.get("timestamp", ""),
                        "status": closest.get("status", ""),
                        "url": closest.get("url", ""),
                        "available_url": f"https://web.archive.org/web/{closest.get('timestamp', '')}/{request.url}",
                    }

        summary = "Available" if result["available"] else "Not found in Wayback Machine"
        return {"success": True, "data": result, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Availability check failed: {str(e)}")


@app.post("/archive/recent")
async def get_recent_snapshots(request: RecentSnapshotsRequest):
    try:
        from datetime import timedelta
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y%m%d")
        snapshots = await query_cdx(request.url, request.max_results, from_date=thirty_days_ago)
        result_data = {
            "target": request.url,
            "period": "last_30_days",
            "total": len(snapshots),
            "snapshots": snapshots,
            "timestamp": datetime.utcnow().isoformat(),
        }
        summary = f"{len(snapshots)} recent snapshot(s) (last 30 days)" if snapshots else "No recent snapshots"
        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recent snapshots query failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008, reload=settings.debug)
