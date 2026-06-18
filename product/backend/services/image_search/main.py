import hashlib
import json
import os
import re
import urllib.parse
from datetime import datetime
from typing import Optional
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from shared.config import get_settings
from shared.http_client import ThothHttpClient

app = FastAPI(
    title="Thoth Image Search Service",
    description="OSINT service for reverse image search and image analysis (EXIF, metadata, hashes).",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = get_settings()
http_client = ThothHttpClient(service_name="image_search")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

TEMP_DIR = "/tmp/thoth_images"
os.makedirs(TEMP_DIR, exist_ok=True)

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".tif", ".ico"}

SEARCH_ENGINES = {
    "google": "https://lens.google.com/uploadbyurl?url={image_url}",
    "yandex": "https://yandex.com/images/search?rpt=imageview&url={image_url}",
    "tineye": "https://tineye.com/search?url={image_url}",
    "bing": "https://www.bing.com/images/search?q=imgurl:{image_url}&view=detailv2",
}


class ImageReverseRequest(BaseModel):
    image_url: str

    @field_validator("image_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("Image URL must start with http:// or https://")
        return v


class ImageInfoRequest(BaseModel):
    image_url: str

    @field_validator("image_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("Image URL must start with http:// or https://")
        return v


async def fetch_image_metadata(image_url: str) -> dict:
    result = {"url": image_url, "content_type": None, "size": None, "width": None, "height": None}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.head(image_url, headers={"User-Agent": USER_AGENT})
            if resp.status_code == 200:
                result["content_type"] = resp.headers.get("content-type")
                content_length = resp.headers.get("content-length")
                if content_length:
                    result["size"] = int(content_length)
    except Exception:
        pass
    return result


def extract_exif(filepath: str) -> dict:
    try:
        from PIL import Image, ExifTags
        img = Image.open(filepath)
        info = {
            "format": img.format,
            "mode": img.mode,
            "width": img.width,
            "height": img.height,
            "size_bytes": os.path.getsize(filepath),
        }

        exif_data = img._getexif()
        if exif_data:
            exif = {}
            for tag_id, value in exif_data.items():
                tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="replace")
                    except Exception:
                        value = str(value)
                exif[tag_name] = str(value)[:500]

            info["exif"] = exif

            if "GPSInfo" in exif:
                import struct
                gps = exif_data.get(0x8825, {})
                if gps:
                    def dms_to_decimal(dms_tuple, ref):
                        try:
                            d, m, s = dms_tuple
                            decimal = float(d) + float(m) / 60.0 + float(s) / 3600.0
                            if ref in ("S", "W"):
                                decimal = -decimal
                            return round(decimal, 6)
                        except Exception:
                            return None

                    lat = dms_to_decimal(gps.get(2), gps.get(1, "N"))
                    lon = dms_to_decimal(gps.get(4), gps.get(3, "E"))
                    if lat and lon:
                        info["gps"] = {"latitude": lat, "longitude": lon}

        return info
    except ImportError:
        return {"error": "PIL/Pillow not available"}
    except Exception as e:
        return {"error": str(e)[:200]}


def compute_hashes(filepath: str) -> dict:
    hashes = {}
    try:
        with open(filepath, "rb") as f:
            data = f.read()
        hashes["md5"] = hashlib.md5(data).hexdigest()
        hashes["sha1"] = hashlib.sha1(data).hexdigest()
        hashes["sha256"] = hashlib.sha256(data).hexdigest()
    except Exception as e:
        hashes["error"] = str(e)[:200]
    return hashes


@app.get("/temp/{filename}")
async def serve_temp_image(filename: str):
    filepath = os.path.join(TEMP_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)


@app.on_event("startup")
async def startup():
    pass


@app.get("/")
async def root():
    return {
        "service": "Thoth Image Search Service",
        "version": "2.0.0",
        "endpoints": [
            "GET /health",
            "POST /search/reverse",
            "POST /search/metadata",
            "POST /search/upload",
            "GET /temp/{filename}",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "image_search", "timestamp": datetime.utcnow().isoformat()}


@app.post("/search/reverse")
async def reverse_search(request: ImageReverseRequest):
    try:
        encoded_url = urllib.parse.quote(request.image_url, safe="")
        search_links = {}
        for engine, url_template in SEARCH_ENGINES.items():
            search_links[engine] = url_template.format(image_url=encoded_url)

        metadata = await fetch_image_metadata(request.image_url)

        result_data = {
            "target": request.image_url,
            "search_links": search_links,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = [f"Liens générés pour {len(search_links)} moteurs"]
        if metadata.get("content_type"):
            parts.append(f"Type: {metadata['content_type']}")
        if metadata.get("size"):
            parts.append(f"{round(metadata['size'] / 1024, 1)} KB")
        summary = " · ".join(parts)

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reverse search failed: {str(e)}")


@app.post("/search/analyze")
async def analyze_image(
    image_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    try:
        if not image_url and not file:
            raise HTTPException(status_code=400, detail="Provide either an image URL or upload a file")

        result = {"timestamp": datetime.utcnow().isoformat()}

        if file:
            ext = os.path.splitext(file.filename or "image.jpg")[1].lower()
            if ext not in VALID_EXTENSIONS:
                ext = ".jpg"
            filename = f"{uuid4().hex}{ext}"
            filepath = os.path.join(TEMP_DIR, filename)
            content = await file.read()
            with open(filepath, "wb") as f:
                f.write(content)

            exif_info = extract_exif(filepath)
            hashes = compute_hashes(filepath)

            temp_relative = f"/temp/{filename}"
            encoded = urllib.parse.quote(f"/temp/{filename}", safe="")
            search_links = {}
            for engine, url_template in SEARCH_ENGINES.items():
                search_links[engine] = url_template.format(image_url="")
            search_links["note"] = "Hébergez l'image publiquement pour utiliser les liens de recherche"

            result.update({
                "source": "upload",
                "filename": file.filename or filename,
                "temp_url": temp_relative,
                "size_bytes": len(content),
                "size_kb": round(len(content) / 1024, 1),
                "exif": exif_info,
                "hashes": hashes,
                "search_links": search_links,
            })

            parts = []
            if exif_info.get("format"):
                parts.append(f"{exif_info['format']} {exif_info.get('width', '?')}x{exif_info.get('height', '?')}")
            if exif_info.get("exif", {}).get("DateTimeOriginal"):
                parts.append(f"Date: {exif_info['exif']['DateTimeOriginal']}")
            if exif_info.get("gps"):
                parts.append("GPS ✓")
            parts.append(f"{round(len(content) / 1024, 1)} KB")
            summary = " · ".join(parts)

        if image_url:
            encoded_url = urllib.parse.quote(image_url, safe="")
            search_links = {}
            for engine, url_template in SEARCH_ENGINES.items():
                search_links[engine] = url_template.format(image_url=encoded_url)

            metadata = await fetch_image_metadata(image_url)

            url_result = {
                "source": "url",
                "target": image_url,
                "search_links": search_links,
                "metadata": metadata,
            }

            if file:
                result["url_analysis"] = url_result
            else:
                result.update(url_result)

            if not file:
                parts = [f"Liens générés pour {len(search_links)} moteurs"]
                if metadata.get("content_type"):
                    parts.append(f"Type: {metadata['content_type']}")
                if metadata.get("size"):
                    parts.append(f"{round(metadata['size'] / 1024, 1)} KB")
                summary = " · ".join(parts)

        return {"success": True, "data": result, "summary": summary}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/search/metadata")
async def image_metadata(request: ImageInfoRequest):
    try:
        metadata = await fetch_image_metadata(request.image_url)
        result_data = {
            "target": request.image_url,
            "metadata": metadata,
            "timestamp": datetime.utcnow().isoformat(),
        }
        parts = []
        if metadata.get("content_type"):
            parts.append(f"Type: {metadata['content_type']}")
        if metadata.get("size"):
            parts.append(f"Taille: {round(metadata['size'] / 1024, 1)} KB")
        summary = " · ".join(parts) if parts else "Image accessible"
        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata fetch failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009, reload=settings.debug)
