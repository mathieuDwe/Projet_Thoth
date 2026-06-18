import pytest
from httpx import AsyncClient, ASGITransport
from services.dns_investigator.main import app


@pytest.fixture
def client(init_db):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "dns_investigator"


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_investigate_domain_valid(client):
    resp = await client.post("/investigate/domain", json={
        "domain": "example.com",
        "include_subdomains": False,
        "include_whois": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data


@pytest.mark.asyncio
async def test_investigate_domain_invalid(client):
    resp = await client.post("/investigate/domain", json={"domain": "not-a-domain"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_investigate_domain_empty(client):
    resp = await client.post("/investigate/domain", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_investigate_domain_with_all_options(client):
    resp = await client.post("/investigate/domain", json={
        "domain": "google.com",
        "include_subdomains": True,
        "include_whois": True,
        "include_dnssec": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_investigate_domain_long(client):
    resp = await client.post("/investigate/domain", json={"domain": "a" * 300 + ".com"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_save_report(client):
    resp = await client.post("/report", json={
        "target": "example.com",
        "service": "dns_investigator",
        "data": {"dns_records": {}},
        "summary": "DNS investigation complete",
        "severity": "info",
        "score": 0.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "report_id" in data


@pytest.mark.asyncio
async def test_save_report_invalid(client):
    resp = await client.post("/report", json={})
    assert resp.status_code == 422
