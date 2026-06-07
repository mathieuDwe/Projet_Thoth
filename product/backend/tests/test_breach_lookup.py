import pytest
from httpx import AsyncClient, ASGITransport
from services.breach_lookup.main import app


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
    assert data["service"] == "breach_lookup"


@pytest.mark.asyncio
async def test_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data
    assert "endpoints" in data


@pytest.mark.asyncio
async def test_lookup_email_invalid(client):
    resp = await client.post("/lookup/email", json={"email": "not-an-email"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_lookup_email_valid(client):
    resp = await client.post("/lookup/email", json={"email": "test@example.com"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data


@pytest.mark.asyncio
async def test_lookup_username_invalid(client):
    resp = await client.post("/lookup/username", json={"username": "a"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_lookup_username_valid(client):
    resp = await client.post("/lookup/username", json={"username": "testuser"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_save_report(client):
    resp = await client.post("/report", json={
        "target": "test@example.com",
        "service": "breach_lookup",
        "data": {"breaches": []},
        "summary": "No breaches found",
        "severity": "info",
        "score": 0.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "report_id" in data


@pytest.mark.asyncio
async def test_lookup_email_empty(client):
    resp = await client.post("/lookup/email", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_lookup_username_empty(client):
    resp = await client.post("/lookup/username", json={})
    assert resp.status_code == 422
