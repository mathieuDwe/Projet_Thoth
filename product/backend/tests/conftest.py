"""Fixtures globales pour les tests de la plateforme OSINT Thoth.

Ce fichier fournit toutes les fixtures nécessaires aux 4 niveaux de tests :
- Unitaires (mocks HTTP via aresponses)
- Intégration (base de données SQLite temporaire)
- Fonctionnels (client HTTP asynchrone)
- Résilience (timeouts, rate limiting)
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock, patch

import aresponses
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient, Response

# ──────────────────────────────────────────────
# Fixtures de configuration et d'environnement
# ──────────────────────────────────────────────


@pytest.fixture(scope="session")
def test_env() -> Generator[None, None, None]:
    """Configure l'environnement de test avec des valeurs par défaut."""
    import tempfile, os
    _tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp_db.close()
    env_vars = {
        "DEBUG": "false",
        "LOG_LEVEL": "ERROR",
        "DB_URL": f"sqlite+aiosqlite:///{_tmp_db.name}",
        "MAX_TIMEOUT": "5",
        "MAX_RETRIES": "1",
        "RATE_LIMIT_RPS": "100",
        "BREACH_DB_PATH": "/tmp/test_breach_db.json",
        "REPORT_STORAGE_PATH": "/tmp/test_reports",
        "FORCE_ASYNC_BACKEND": "asyncio",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield
    if os.path.exists(_tmp_db.name):
        os.unlink(_tmp_db.name)


@pytest.fixture(autouse=True)
def reset_settings_cache(test_env):
    """Reset le cache des settings et de l'engine à chaque test pour isoler la configuration."""
    from shared.config import get_settings, Settings
    from shared.database import reset_engine
    get_settings.cache_clear()
    reset_engine()
    yield
    get_settings.cache_clear()
    reset_engine()


@pytest_asyncio.fixture
async def init_db():
    """Initialise la base de données de test."""
    from shared.database import init_db as _init
    await _init()
    yield
    from shared.database import get_engine, Base
    engine = get_engine()
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# ──────────────────────────────────────────────
# Fixtures de base de données SQLite temporaire
# ──────────────────────────────────────────────


@pytest_asyncio.fixture
async def temp_db():
    """Crée une base de données SQLite temporaire pour les tests d'intégration.

    Retourne le chemin et la session pour interagir avec la BDD de test.
    Les tables sont créées au setUp et détruites au tearDown.
    """
    db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = db_file.name
    db_file.close()

    # Surcharge l'URL de connexion pour pointer sur le fichier temporaire
    test_db_url = f"sqlite+aiosqlite:///{db_path}"

    from shared.database import create_async_engine, async_sessionmaker, Base
    from shared.models import Report  # noqa: ensure models are loaded

    engine = create_async_engine(test_db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Création des tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield {
            "engine": engine,
            "session_factory": session_factory,
            "db_path": db_path,
        }
    finally:
        # Nettoyage
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest_asyncio.fixture
async def db_session(temp_db):
    """Fournit une session de base de données pour les tests."""
    session_factory = temp_db["session_factory"]
    async with session_factory() as session:
        yield session


# ──────────────────────────────────────────────
# Fixtures pour les données de test
# ──────────────────────────────────────────────


@pytest.fixture
def sample_report_data() -> Dict:
    """Données standards pour créer un rapport de test."""
    return {
        "target": "test@example.com",
        "service": "breach_lookup",
        "data": {
            "breaches": [
                {
                    "name": "TestBreach",
                    "domain": "test.com",
                    "date": "2020-01-01",
                    "description": "Test breach for unit testing",
                }
            ],
            "found": True,
        },
        "summary": "1 breach found for test@example.com",
        "severity": "medium",
        "score": 5.0,
    }


@pytest.fixture
def sample_report_data_dns() -> Dict:
    """Données de test pour un rapport DNS."""
    return {
        "target": "example.com",
        "service": "dns_investigator",
        "data": {
            "a_records": ["93.184.216.34"],
            "aaaa_records": ["2606:2800:220:1:248:1893:25c8:1946"],
            "mx_records": ["mail.example.com"],
            "ns_records": ["ns1.example.com"],
            "whois": {
                "registrar": "Example Registrar",
                "creation_date": "1997-09-15",
                "expiration_date": "2028-09-14",
            },
        },
        "summary": "DNS analysis for example.com: 4 record types found",
        "severity": "info",
        "score": 0.0,
    }


@pytest.fixture
def sample_report_data_ip() -> Dict:
    """Données de test pour un rapport IP geoloc."""
    return {
        "target": "8.8.8.8",
        "service": "ip_geoloc",
        "data": {
            "ip": "8.8.8.8",
            "hostname": "dns.google",
            "city": "Mountain View",
            "region": "California",
            "country": "US",
            "loc": "37.4056,-122.0775",
            "org": "AS15169 Google LLC",
            "postal": "94043",
            "timezone": "America/Los_Angeles",
        },
        "summary": "IP 8.8.8.8 located in Mountain View, California, US",
        "severity": "info",
        "score": 0.0,
    }


@pytest.fixture
def sample_report_data_social() -> Dict:
    """Données de test pour un rapport social harvester."""
    return {
        "target": "johndoe",
        "service": "social_harvester",
        "data": {
            "profiles": [
                {
                    "platform": "github",
                    "url": "https://github.com/johndoe",
                    "username": "johndoe",
                    "found": True,
                },
                {
                    "platform": "twitter",
                    "url": "https://twitter.com/johndoe",
                    "username": "johndoe",
                    "found": True,
                },
            ],
            "total_found": 2,
        },
        "summary": "2 social profiles found for johndoe",
        "severity": "info",
        "score": 0.0,
    }


# ──────────────────────────────────────────────
# Fixtures de mocks HTTP (aresponses)
# ──────────────────────────────────────────────


@pytest_asyncio.fixture
async def aresponses_client():
    """Fournit un mock HTTP aresponses pour simuler les APIs externes.

    Utilisation :
        async with aresponses_client as mock:
            mock.add("example.com", "/api", "get", response)
            result = await client.get("https://example.com/api")
    """
    async with aresponses.ResponsesMockServer() as mock:
        yield mock


@pytest.fixture
def mock_breach_db() -> Generator[None, None, None]:
    """Crée une base de breaches JSON factice dans /tmp."""
    breach_data = {
        "breaches": [
            {
                "Name": "TestBreach",
                "Domain": "test.com",
                "BreachDate": "2020-01-01",
                "Description": "A test breach",
                "DataClasses": ["Emails", "Passwords"],
                "IsVerified": True,
                "PwnCount": 1000,
            },
            {
                "Name": "AnotherBreach",
                "Domain": "example.com",
                "BreachDate": "2019-06-15",
                "Description": "Another test",
                "DataClasses": ["Usernames"],
                "IsVerified": False,
                "PwnCount": 500,
            },
        ]
    }
    db_path = "/tmp/test_breach_db.json"
    with open(db_path, "w") as f:
        json.dump(breach_data, f)
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


# ──────────────────────────────────────────────
# Fixtures pour les clients HTTP de test
# ──────────────────────────────────────────────


@pytest_asyncio.fixture
async def http_client() -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP asynchrone générique pour les tests."""
    async with AsyncClient() as client:
        yield client


@pytest_asyncio.fixture
async def shared_http_client():
    """Instance du ThothHttpClient avec des timeouts réduits pour les tests."""
    from shared.http_client import ThothHttpClient

    client = ThothHttpClient(service_name="test")
    # Forcer des timeouts courts pour les tests
    client.settings.max_timeout = 5.0
    client.settings.max_retries = 1
    client.settings.rate_limit_rps = 1000  # Désactive le rate limiting en test
    try:
        yield client
    finally:
        await client.close()


# ──────────────────────────────────────────────
# Fixtures pour les réponses HTTP simulées
# ──────────────────────────────────────────────


@pytest.fixture
def breach_api_response() -> Dict:
    """Réponse simulée de l'API Have I Been Pwned."""
    return [
        {
            "Name": "Adobe",
            "Domain": "adobe.com",
            "BreachDate": "2013-10-04",
            "Description": "In October 2013...",
            "DataClasses": ["Email addresses", "Password hints", "Passwords"],
            "IsVerified": True,
            "PwnCount": 152445165,
        }
    ]


@pytest.fixture
def ipinfo_response() -> Dict:
    """Réponse simulée de l'API ipinfo.io."""
    return {
        "ip": "8.8.8.8",
        "hostname": "dns.google",
        "city": "Mountain View",
        "region": "California",
        "country": "US",
        "loc": "37.4056,-122.0775",
        "org": "AS15169 Google LLC",
        "postal": "94043",
        "timezone": "America/Los_Angeles",
    }


@pytest.fixture
def abuseipdb_response() -> Dict:
    """Réponse simulée de l'API AbuseIPDB."""
    return {
        "data": {
            "ipAddress": "8.8.8.8",
            "isPublic": True,
            "ipVersion": 4,
            "isWhitelisted": True,
            "abuseConfidenceScore": 0,
            "countryCode": "US",
            "usageType": "Search Engine",
            "isp": "Google LLC",
            "domain": "google.com",
            "totalReports": 0,
            "lastReportedAt": None,
        }
    }


# ──────────────────────────────────────────────
# Fixtures de test de résilience
# ──────────────────────────────────────────────


@pytest.fixture
def rate_limit_response_headers() -> Dict:
    """Headers simulés pour une réponse 429 Rate Limited."""
    return {
        "Retry-After": "1",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": str(asyncio.get_event_loop().time() + 10),
    }


@pytest.fixture
def slow_response_data() -> Dict:
    """Données pour simuler une réponse lente (timeout)."""
    return {
        "delay": 10,  # secondes
        "data": {"status": "ok"},
    }


# ──────────────────────────────────────────────
# Fixtures pour la validation terrain
# ──────────────────────────────────────────────


@pytest.fixture
def real_targets() -> Dict[str, str]:
    """Cibles réelles pour les tests de connectivité terrain.

    WARNING: Ces tests nécessitent une connexion Internet active.
    """
    return {
        "email": "test@example.com",
        "username": "john_doe",
        "domain": "example.com",
        "ip": "8.8.8.8",
        "invalid_email": "not-an-email",
        "invalid_domain": "invalid-domain-xyz-123.com",
        "invalid_ip": "999.999.999.999",
        "private_ip": "192.168.1.1",
        "localhost": "127.0.0.1",
    }


# ──────────────────────────────────────────────
# Fixtures utilitaires pour les tests partagés
# ──────────────────────────────────────────────


@pytest.fixture
def report_model_class():
    """Retourne la classe Report pour les tests unitaires du modèle."""
    from shared.models import Report
    return Report


@pytest.fixture
def settings_instance():
    """Retourne une instance des settings de test."""
    from shared.config import get_settings
    return get_settings()


@pytest.fixture
def anyio_backend():
    """Configure anyio pour les tests pytest-asyncio."""
    return "asyncio"
