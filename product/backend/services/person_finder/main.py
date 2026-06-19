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
    title="Thoth Person Finder Service",
    description="OSINT service that searches for people across the web: finds images, news articles, "
                "social media mentions, and web references related to a person's name or username.",
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
http_client = ThothHttpClient(service_name="person_finder")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


class PersonSearchRequest(BaseModel):
    name: str
    max_results: int = 10

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        if len(v) > 200:
            raise ValueError("Name is too long")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("max_results must be between 1 and 50")
        return v


class ImageSearchRequest(BaseModel):
    query: str
    max_results: int = 10

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Query must be at least 2 characters")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("max_results must be between 1 and 50")
        return v


class ArticleSearchRequest(BaseModel):
    query: str
    max_results: int = 10

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Query must be at least 2 characters")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("max_results must be between 1 and 50")
        return v


async def search_images_duckduckgo(query: str, max_results: int = 10) -> list[dict]:
    """Search for images using DuckDuckGo image search API."""
    results = []
    try:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://duckduckgo.com/",
        }
        params = {
            "q": query,
            "o": "json",
            "vqd": "",
            "f": ",,,",
            "p": "1",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://duckduckgo.com/i.js",
                params=params,
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", [])[:max_results]:
                    image_url = item.get("image", "")
                    thumbnail = item.get("thumbnail", item.get("image", ""))
                    if image_url:
                        results.append({
                            "url": item.get("url", image_url),
                            "thumbnail": thumbnail,
                            "image": image_url,
                            "alt": item.get("title", query),
                            "source": "duckduckgo",
                            "width": item.get("width"),
                            "height": item.get("height"),
                        })
    except Exception:
        pass

    if not results:
        results = await search_images_bing(query, max_results)

    return results


async def search_images_bing(query: str, max_results: int = 10) -> list[dict]:
    """Fallback image search using Bing."""
    results = []
    try:
        headers = {"User-Agent": USER_AGENT}
        params = {"q": query, "form": "HDRSC2", "first": "1"}

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                "https://www.bing.com/images/search",
                params=params,
                headers=headers,
            )
            if resp.status_code == 200:
                html = resp.text
                img_matches = re.findall(
                    r'<a[^>]*class="thumb"[^>]*href="(https?://[^"]+)"[^>]*>.*?<img[^>]*src="(https?://[^"]+)"',
                    html,
                )
                for href, src in img_matches[:max_results]:
                    results.append({
                        "url": href,
                        "thumbnail": src,
                        "alt": query,
                        "source": "bing",
                    })

                if not results:
                    img_matches = re.findall(
                        r'<img[^>]*class="mimg"[^>]*src="(https?://[^"]+)"[^>]*alt="([^"]*)"',
                        html,
                    )
                    for src, alt in img_matches[:max_results]:
                        results.append({
                            "url": src,
                            "thumbnail": src,
                            "image": src,
                            "alt": alt or query,
                            "source": "bing",
                        })
    except Exception:
        pass

    return results


async def search_articles_duckduckgo(query: str, max_results: int = 10) -> list[dict]:
    """Search for articles/news using DuckDuckGo web search."""
    results = []
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {"User-Agent": USER_AGENT}

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                return results

            html = resp.text
            result_blocks = re.findall(
                r'<a[^>]*class="result__a"[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                html,
                re.DOTALL,
            )

            for url_href, title_html in result_blocks[:max_results]:
                title_clean = re.sub(r'<[^>]+>', '', title_html).strip()
                if title_clean:
                    results.append({
                        "title": title_clean,
                        "url": url_href,
                        "source": "duckduckgo",
                    })

            if not results:
                snippets = re.findall(
                    r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                    html,
                )
                seen_urls = set()
                for url_href, title_text in snippets:
                    title_clean = re.sub(r'<[^>]+>', '', title_text).strip()
                    if title_clean and url_href not in seen_urls and len(results) < max_results:
                        seen_urls.add(url_href)
                        if not any(skip in url_href for skip in ['duckduckgo.com', 'javascript:']):
                            results.append({
                                "title": title_clean,
                                "url": url_href,
                                "source": "duckduckgo",
                            })
    except Exception:
        pass

    return results


async def search_wikipedia(query: str, max_results: int = 5) -> list[dict]:
    """Search Wikipedia for articles about the person."""
    results = []
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": max_results,
            "srprop": "snippet|timestamp",
        }
        headers = {"User-Agent": "ThothOSINT/1.0 (OSINT Platform)"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("query", {}).get("search", []):
                    snippet_clean = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                    results.append({
                        "title": item.get("title", ""),
                        "url": f"https://en.wikipedia.org/wiki/{item.get('title', '').replace(' ', '_')}",
                        "snippet": snippet_clean,
                        "timestamp": item.get("timestamp", ""),
                        "source": "wikipedia",
                    })
    except Exception:
        pass

    return results


async def search_news_brave(query: str, max_results: int = 10) -> list[dict]:
    """Search news using Brave Search API (free tier, no key required for basic)."""
    results = []
    try:
        url = "https://search.brave.com/api/search"
        params = {
            "q": query,
            "source": "news",
            "count": min(max_results, 20),
        }
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", [])[:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("description", ""),
                        "age": item.get("age", ""),
                        "source": item.get("source", "brave"),
                    })
    except Exception:
        pass

    return results


def compute_severity_and_score(image_count: int, article_count: int, wiki_count: int) -> tuple[str, float]:
    total = image_count + article_count + wiki_count
    if total >= 20:
        return "high", 8.0
    elif total >= 10:
        return "medium", 5.0
    elif total >= 1:
        return "low", 2.0
    return "info", 0.0


@app.on_event("startup")
async def startup():
    pass


@app.get("/")
async def root():
    return {
        "service": "Thoth Person Finder Service",
        "version": "1.0.0",
        "endpoints": [
            "GET /health",
            "POST /search/person",
            "POST /search/images",
            "POST /search/articles",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "person_finder", "timestamp": datetime.utcnow().isoformat()}


@app.post("/search/person")
async def search_person(request: PersonSearchRequest):
    """Search for a person across images, articles, and Wikipedia."""
    try:
        image_task = search_images_duckduckgo(request.name, request.max_results)
        article_task = search_articles_duckduckgo(request.name, request.max_results)
        wiki_task = search_wikipedia(request.name, 5)
        brave_task = search_news_brave(request.name, request.max_results)

        image_results, article_results, wiki_results, brave_results = await asyncio.gather(
            image_task, article_task, wiki_task, brave_task, return_exceptions=True,
        )

        if isinstance(image_results, Exception):
            image_results = []
        if isinstance(article_results, Exception):
            article_results = []
        if isinstance(wiki_results, Exception):
            wiki_results = []
        if isinstance(brave_results, Exception):
            brave_results = []

        all_articles = article_results + wiki_results + brave_results

        severity, score = compute_severity_and_score(
            len(image_results), len(all_articles), len(wiki_results),
        )

        result_data = {
            "target": request.name,
            "images": {
                "count": len(image_results),
                "results": image_results,
            },
            "articles": {
                "count": len(all_articles),
                "results": all_articles,
            },
            "wikipedia": {
                "count": len(wiki_results),
                "results": wiki_results,
            },
            "severity": severity,
            "score": score,
            "timestamp": datetime.utcnow().isoformat(),
        }

        parts = []
        if image_results:
            parts.append(f"{len(image_results)} image(s) found")
        if all_articles:
            parts.append(f"{len(all_articles)} article(s) found")
        if wiki_results:
            parts.append(f"{len(wiki_results)} Wikipedia article(s)")

        summary = "; ".join(parts) if parts else "No results found"

        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Person search failed: {str(e)}")


@app.post("/search/images")
async def search_images(request: ImageSearchRequest):
    """Search for images of a person or topic."""
    try:
        image_results = await search_images_duckduckgo(request.query, request.max_results)

        result_data = {
            "query": request.query,
            "count": len(image_results),
            "results": image_results,
            "timestamp": datetime.utcnow().isoformat(),
        }

        summary = f"{len(image_results)} image(s) found for '{request.query}'"
        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image search failed: {str(e)}")


@app.post("/search/articles")
async def search_articles(request: ArticleSearchRequest):
    """Search for articles about a person or topic."""
    try:
        article_task = search_articles_duckduckgo(request.query, request.max_results)
        wiki_task = search_wikipedia(request.query, 5)
        brave_task = search_news_brave(request.query, request.max_results)

        article_results, wiki_results, brave_results = await asyncio.gather(
            article_task, wiki_task, brave_task, return_exceptions=True,
        )

        if isinstance(article_results, Exception):
            article_results = []
        if isinstance(wiki_results, Exception):
            wiki_results = []
        if isinstance(brave_results, Exception):
            brave_results = []

        all_results = article_results + wiki_results + brave_results

        result_data = {
            "query": request.query,
            "count": len(all_results),
            "results": all_results,
            "wikipedia": wiki_results,
            "timestamp": datetime.utcnow().isoformat(),
        }

        summary = f"{len(all_results)} article(s) found for '{request.query}'"
        return {"success": True, "data": result_data, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Article search failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown():
    await http_client.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005, reload=settings.debug)
