import asyncio
import json
import re
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from shared.config import get_settings
from shared.http_client import ThothHttpClient

app = FastAPI(
    title="Thoth Phone Analyzer Service",
    description="OSINT service that analyzes phone numbers: format validation, country detection, carrier info, and possible associations.",
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
http_client = ThothHttpClient(service_name="phone_analyzer")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

PREFIX_COUNTRIES = [
    {"prefix": "1", "country": "US/CA", "name": "États-Unis / Canada", "code": "US", "length": 10},
    {"prefix": "33", "country": "FR", "name": "France", "code": "FR", "length": 9},
    {"prefix": "44", "country": "GB", "name": "Royaume-Uni", "code": "GB", "length": 10},
    {"prefix": "49", "country": "DE", "name": "Allemagne", "code": "DE", "length": 10},
    {"prefix": "34", "country": "ES", "name": "Espagne", "code": "ES", "length": 9},
    {"prefix": "39", "country": "IT", "name": "Italie", "code": "IT", "length": 9},
    {"prefix": "31", "country": "NL", "name": "Pays-Bas", "code": "NL", "length": 9},
    {"prefix": "32", "country": "BE", "name": "Belgique", "code": "BE", "length": 9},
    {"prefix": "41", "country": "CH", "name": "Suisse", "code": "CH", "length": 9},
    {"prefix": "351", "country": "PT", "name": "Portugal", "code": "PT", "length": 9},
    {"prefix": "46", "country": "SE", "name": "Suède", "code": "SE", "length": 9},
    {"prefix": "47", "country": "NO", "name": "Norvège", "code": "NO", "length": 8},
    {"prefix": "45", "country": "DK", "name": "Danemark", "code": "DK", "length": 8},
    {"prefix": "358", "country": "FI", "name": "Finlande", "code": "FI", "length": 9},
    {"prefix": "48", "country": "PL", "name": "Pologne", "code": "PL", "length": 9},
    {"prefix": "7", "country": "RU", "name": "Russie", "code": "RU", "length": 10},
    {"prefix": "86", "country": "CN", "name": "Chine", "code": "CN", "length": 11},
    {"prefix": "81", "country": "JP", "name": "Japon", "code": "JP", "length": 10},
    {"prefix": "82", "country": "KR", "name": "Corée du Sud", "code": "KR", "length": 10},
    {"prefix": "91", "country": "IN", "name": "Inde", "code": "IN", "length": 10},
    {"prefix": "55", "country": "BR", "name": "Brésil", "code": "BR", "length": 10},
    {"prefix": "52", "country": "MX", "name": "Mexique", "code": "MX", "length": 10},
    {"prefix": "61", "country": "AU", "name": "Australie", "code": "AU", "length": 9},
    {"prefix": "27", "country": "ZA", "name": "Afrique du Sud", "code": "ZA", "length": 9},
    {"prefix": "212", "country": "MA", "name": "Maroc", "code": "MA", "length": 9},
    {"prefix": "213", "country": "DZ", "name": "Algérie", "code": "DZ", "length": 9},
    {"prefix": "216", "country": "TN", "name": "Tunisie", "code": "TN", "length": 8},
]

CARRIER_PATTERNS = [
    {"pattern": r"^06|^07", "country": "FR", "carrier": "Mobile français"},
    {"pattern": r"^01|^02|^03|^04|^05", "country": "FR", "carrier": "Fixe français"},
]


class PhoneAnalyzeRequest(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        cleaned = re.sub(r"[\s\-\+\(\)\.]", "", v)
        if not cleaned.isdigit():
            raise ValueError("Le numéro ne doit contenir que des chiffres")
        if len(cleaned) < 7 or len(cleaned) > 15:
            raise ValueError("Longueur de numéro invalide")
        return cleaned


def detect_country(number: str) -> Optional[dict]:
    for entry in sorted(PREFIX_COUNTRIES, key=lambda x: -len(x["prefix"])):
        if number.startswith(entry["prefix"]):
            return entry
    return None


def format_international(number: str, country: dict) -> str:
    return f"+{number}"


def format_local(number: str, country: dict) -> str:
    prefix_len = len(country["prefix"])
    national = number[prefix_len:]
    return f"0{national}"


async def search_online(phone: str) -> list[dict]:
    results = []
    try:
        urls = [
            {"name": "Google", "url": f"https://www.google.com/search?q={phone}"},
            {"name": "NumLookup", "url": f"https://www.numlookup.com/{phone}"},
        ]
        for entry in urls:
            results.append({"source": entry["name"], "url": entry["url"], "status": "search_link_generated"})
    except Exception:
        pass
    return results


@app.on_event("startup")
async def startup():
    pass


@app.get("/")
async def root():
    return {
        "service": "Thoth Phone Analyzer Service",
        "version": "1.0.0",
        "endpoints": ["GET /health", "POST /analyze/phone"],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "phone_analyzer", "timestamp": datetime.utcnow().isoformat()}


@app.post("/analyze/phone")
async def analyze_phone(request: PhoneAnalyzeRequest):
    try:
        number = request.phone
        country_info = detect_country(number)
        online_links = await search_online(number)

        result_data = {
            "target": number,
            "international_format": f"+{number}",
            "length": len(number),
            "country": country_info,
            "online_search_links": online_links,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = []
        if country_info:
            parts.append(f"Pays: {country_info['name']} ({country_info['code']})")
            local = f"0{number[len(country_info['prefix']):]}"
            result_data["national_format"] = local
            parts.append(f"National: {local}")
        parts.append(f"+{number}")
        summary = " · ".join(parts)

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Phone analysis failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010, reload=settings.debug)
