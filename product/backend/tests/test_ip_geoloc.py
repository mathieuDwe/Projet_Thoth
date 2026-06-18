import pytest
from httpx import AsyncClient, ASGITransport
from services.ip_geoloc.main import app


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
    assert data["service"] == "ip_geoloc"


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_analyze_ip_valid(client):
    resp = await client.post("/analyze/ip", json={"ip": "8.8.8.8"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data


@pytest.mark.asyncio
async def test_analyze_ip_invalid(client):
    resp = await client.post("/analyze/ip", json={"ip": "999.999.999.999"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analyze_ip_private(client):
    resp = await client.post("/analyze/ip", json={"ip": "192.168.1.1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_analyze_ip_localhost(client):
    resp = await client.post("/analyze/ip", json={"ip": "127.0.0.1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_analyze_ip_empty(client):
    resp = await client.post("/analyze/ip", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analyze_ip_with_ports(client):
    resp = await client.post("/analyze/ip", json={"ip": "8.8.8.8", "scan_ports": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_analyze_bulk_valid(client):
    resp = await client.post("/analyze/bulk", json={
        "ips": ["8.8.8.8", "1.1.1.1"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data


@pytest.mark.asyncio
async def test_analyze_bulk_invalid_ip(client):
    resp = await client.post("/analyze/bulk", json={"ips": ["not-an-ip"]})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analyze_bulk_too_many(client):
    resp = await client.post("/analyze/bulk", json={"ips": [f"8.8.8.{i}" for i in range(51)]})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_save_report(client):
    resp = await client.post("/report", json={
        "target": "8.8.8.8",
        "service": "ip_geoloc",
        "data": {"geolocation": {}},
        "summary": "IP analysis complete",
        "severity": "info",
        "score": 0.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "report_id" in data
