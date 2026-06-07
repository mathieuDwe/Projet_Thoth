import pytest
from httpx import AsyncClient, ASGITransport
from services.social_harvester.main import app


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
    assert data["service"] == "social_harvester"


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data


@pytest.mark.asyncio
async def test_scan_username_valid(client):
    resp = await client.post("/scan/username", json={"username": "johndoe"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data


@pytest.mark.asyncio
async def test_scan_username_invalid_short(client):
    resp = await client.post("/scan/username", json={"username": "a"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_scan_username_invalid_chars(client):
    resp = await client.post("/scan/username", json={"username": "user name!"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_scan_username_empty(client):
    resp = await client.post("/scan/username", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_scan_username_with_platforms(client):
    resp = await client.post("/scan/username", json={
        "username": "testuser",
        "platforms": ["github", "reddit"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_scan_username_invalid_platform(client):
    resp = await client.post("/scan/username", json={
        "username": "testuser",
        "platforms": ["nonexistent"],
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_scan_email_valid(client):
    resp = await client.post("/scan/email", json={"email": "test@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_scan_email_invalid(client):
    resp = await client.post("/scan/email", json={"email": "not-email"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_save_report(client):
    resp = await client.post("/report", json={
        "target": "johndoe",
        "service": "social_harvester",
        "data": {"profiles": []},
        "summary": "No profiles found",
        "severity": "info",
        "score": 0.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "report_id" in data
