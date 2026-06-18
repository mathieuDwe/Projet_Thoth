import pytest
from httpx import AsyncClient, ASGITransport
from services.gateway.main import app


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
    assert data["service"] == "gateway"


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data
    assert "endpoints" in data
    assert "microservices" in data


@pytest.mark.asyncio
async def test_status(client):
    resp = await client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall" in data
    assert "services" in data


@pytest.mark.asyncio
async def test_investigate_global_empty(client):
    resp = await client.post("/investigate/global", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_investigate_global_email(client):
    resp = await client.post("/investigate/global", json={"email": "test@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_investigate_global_domain(client):
    resp = await client.post("/investigate/global", json={"domain": "example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_investigate_global_ip(client):
    resp = await client.post("/investigate/global", json={"ip": "8.8.8.8"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_investigate_global_all(client):
    resp = await client.post("/investigate/global", json={
        "email": "test@example.com",
        "username": "testuser",
        "domain": "example.com",
        "ip": "8.8.8.8",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_investigate_global_invalid_email(client):
    resp = await client.post("/investigate/global", json={"email": "not-email"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_investigate_global_invalid_domain(client):
    resp = await client.post("/investigate/global", json={"domain": "not_a_domain"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_investigate_global_invalid_ip(client):
    resp = await client.post("/investigate/global", json={"ip": "999.999.999.999"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_reports(client):
    resp = await client.get("/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert "reports" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_report_not_found(client):
    resp = await client.get("/reports/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_report_not_found(client):
    resp = await client.delete("/reports/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_export_report_not_found(client):
    resp = await client.get("/reports/nonexistent-id/export", params={"format": "json"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_reports_with_filters(client):
    resp = await client.get("/reports", params={
        "service": "breach_lookup",
        "severity": "high",
        "limit": 10,
        "offset": 0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "reports" in data


@pytest.mark.asyncio
async def test_export_invalid_format(client):
    resp = await client.get("/reports/nonexistent-id/export", params={"format": "xml"})
    assert resp.status_code == 422
