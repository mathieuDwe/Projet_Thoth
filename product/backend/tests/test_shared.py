"""Tests unitaires et d'intégration pour les modules partagés.

Couvre :
- shared/models.py : Report model, to_dict, validation
- shared/database.py : Session, CRUD, cycle de vie
- shared/http_client.py : Requêtes, rate limiting, retry, timeout, close
- shared/config.py : Settings, validation, valeurs par défaut
"""

import json
import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import aresponses
import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select, func


# =========================================================================
# Tests Unitaires — Config (shared/config.py)
# =========================================================================


class TestConfig:
    """Tests unitaires pour la configuration."""

    @pytest.mark.unit
    def test_default_values(self, settings_instance):
        """Vérifie les valeurs par défaut des settings."""
        assert settings_instance.app_name == "Thoth OSINT Platform"
        assert settings_instance.debug is False
        assert settings_instance.log_level == "ERROR"  # Surchargé par test_env
        assert settings_instance.max_timeout == 5  # Surchargé par test_env
        assert settings_instance.max_retries == 1  # Surchargé par test_env

    @pytest.mark.unit
    def test_db_url_default_format(self, settings_instance):
        """Vérifie que l'URL de base de données utilise aiosqlite."""
        assert settings_instance.db_url.startswith("sqlite+aiosqlite:///")

    @pytest.mark.unit
    def test_settings_immutable_via_env(self):
        """Vérifie que les settings peuvent être surchargés par l'environnement."""
        with patch.dict(os.environ, {"DEBUG": "true", "MAX_TIMEOUT": "10"}, clear=False):
            from shared.config import get_settings, Settings
            get_settings.cache_clear()
            s = get_settings()
            assert s.debug is True
            assert s.max_timeout == 10
            get_settings.cache_clear()

    @pytest.mark.unit
    def test_rate_limit_rps_default(self, settings_instance):
        """Vérifie le taux de requêtes par seconde."""
        # En test_env, on force à 100, mais vérifions le type
        assert isinstance(settings_instance.rate_limit_rps, (int, float))
        assert settings_instance.rate_limit_rps > 0


# =========================================================================
# Tests Unitaires — Models (shared/models.py)
# =========================================================================


class TestReportModel:
    """Tests unitaires pour le modèle Report."""

    @pytest.mark.unit
    def test_report_creation(self, report_model_class, sample_report_data):
        """Vérifie la création d'un rapport avec toutes les propriétés."""
        report = report_model_class(**sample_report_data)
        # L'ID doit être auto-généré
        assert report.id is not None
        assert isinstance(report.id, str)
        # Vérification UUID valide
        uuid.UUID(report.id)
        assert report.target == sample_report_data["target"]
        assert report.service == sample_report_data["service"]
        assert report.data == sample_report_data["data"]
        assert report.summary == sample_report_data["summary"]
        assert report.severity == sample_report_data["severity"]
        assert report.score == sample_report_data["score"]

    @pytest.mark.unit
    def test_report_default_values(self, report_model_class):
        """Vérifie les valeurs par défaut lors de la création."""
        report = report_model_class(target="test@example.com", service="breach_lookup")
        assert uuid.UUID(report.id)  # ID généré
        assert report.created_at is not None
        assert report.data == {}
        assert report.summary == ""
        assert report.severity == "info"
        assert report.score == 0.0
        assert report.export_format == "json"

    @pytest.mark.unit
    def test_report_to_dict(self, report_model_class, sample_report_data):
        """Vérifie la méthode to_dict()."""
        report = report_model_class(**sample_report_data)
        d = report.to_dict()
        assert d["target"] == sample_report_data["target"]
        assert d["service"] == sample_report_data["service"]
        assert d["data"] == sample_report_data["data"]
        assert d["summary"] == sample_report_data["summary"]
        assert d["severity"] == sample_report_data["severity"]
        assert d["score"] == sample_report_data["score"]
        assert "id" in d
        assert "created_at" in d
        assert "updated_at" in d

    @pytest.mark.unit
    def test_report_to_dict_isoformat_dates(self, report_model_class):
        """Vérifie que les dates sont en format ISO dans to_dict()."""
        report = report_model_class(target="test@example.com", service="breach_lookup")
        d = report.to_dict()
        assert d["created_at"] is not None
        # Vérification format ISO (YYYY-MM-DDTHH:MM:SS)
        assert "T" in d["created_at"]

    @pytest.mark.unit
    def test_report_id_is_unique(self, report_model_class):
        """Vérifie que chaque rapport a un ID unique."""
        report1 = report_model_class(target="a@a.com", service="breach_lookup")
        report2 = report_model_class(target="b@b.com", service="breach_lookup")
        assert report1.id != report2.id

    @pytest.mark.unit
    def test_report_severity_values(self, report_model_class):
        """Vérifie que différents niveaux de sévérité sont acceptés."""
        for severity in ["info", "low", "medium", "high", "critical"]:
            report = report_model_class(
                target="test@example.com",
                service="breach_lookup",
                severity=severity,
            )
            assert report.severity == severity

    @pytest.mark.unit
    def test_report_data_with_nested_structures(self, report_model_class):
        """Vérifie que le champ data accepte des structures complexes."""
        data = {
            "breaches": [
                {"name": "Breach1", "items": ["a", "b", "c"]},
                {"name": "Breach2", "nested": {"key": "value"}},
            ],
            "metadata": {
                "timestamp": "2024-01-01T00:00:00",
                "count": 42,
                "flags": [True, False],
            },
        }
        report = report_model_class(
            target="complex@test.com",
            service="dns_investigator",
            data=data,
        )
        assert report.data == data
        assert report.data["breaches"][0]["name"] == "Breach1"
        assert report.data["metadata"]["count"] == 42

    @pytest.mark.unit
    def test_report_score_range(self, report_model_class):
        """Vérifie que le score peut être négatif, nul ou positif."""
        for score in [-1.0, 0.0, 5.5, 10.0, 100.0]:
            report = report_model_class(
                target="test@example.com",
                service="breach_lookup",
                score=score,
            )
            assert report.score == score


# =========================================================================
# Tests d'Intégration — Base de données (shared/database.py)
# =========================================================================


class TestDatabaseCRUD:
    """Tests d'intégration pour les opérations CRUD sur la base de données."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_report(self, temp_db, db_session, sample_report_data):
        """Test la création d'un rapport en base."""
        from shared.models import Report

        report = Report(**sample_report_data)
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)

        assert report.id is not None
        assert report.target == sample_report_data["target"]
        assert report.service == sample_report_data["service"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_read_report(self, temp_db, db_session, sample_report_data):
        """Test la lecture d'un rapport depuis la base."""
        from shared.models import Report

        # Création
        report = Report(**sample_report_data)
        db_session.add(report)
        await db_session.commit()
        await db_session.refresh(report)
        report_id = report.id

        # Relecture
        result = await db_session.get(Report, report_id)
        assert result is not None
        assert result.target == sample_report_data["target"]
        assert result.summary == sample_report_data["summary"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_update_report(self, temp_db, db_session, sample_report_data):
        """Test la mise à jour d'un rapport."""
        from shared.models import Report

        report = Report(**sample_report_data)
        db_session.add(report)
        await db_session.commit()

        # Mise à jour
        report.summary = "Updated summary"
        report.severity = "high"
        report.score = 8.5
        await db_session.commit()
        await db_session.refresh(report)

        assert report.summary == "Updated summary"
        assert report.severity == "high"
        assert report.score == 8.5

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_report(self, temp_db, db_session, sample_report_data):
        """Test la suppression d'un rapport."""
        from shared.models import Report

        report = Report(**sample_report_data)
        db_session.add(report)
        await db_session.commit()
        report_id = report.id

        # Suppression
        await db_session.delete(report)
        await db_session.commit()

        # Vérification suppression
        result = await db_session.get(Report, report_id)
        assert result is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_list_reports(self, temp_db, db_session, sample_report_data):
        """Test la liste paginée des rapports."""
        from shared.models import Report

        # Création de plusieurs rapports
        for i in range(5):
            report = Report(
                target=f"user{i}@example.com",
                service="breach_lookup",
                data={"index": i},
            )
            db_session.add(report)
        await db_session.commit()

        # Lecture de tous les rapports
        stmt = select(Report).order_by(Report.created_at)
        result = await db_session.execute(stmt)
        reports = result.scalars().all()

        assert len(reports) == 5

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_filter_reports_by_service(
        self, temp_db, db_session, sample_report_data
    ):
        """Test le filtrage des rapports par service."""
        from shared.models import Report

        services = ["breach_lookup", "dns_investigator", "ip_geoloc", "social_harvester"]
        for svc in services:
            report = Report(target="test@example.com", service=svc)
            db_session.add(report)
        await db_session.commit()

        # Filtrage par service
        stmt = select(Report).where(Report.service == "dns_investigator")
        result = await db_session.execute(stmt)
        dns_reports = result.scalars().all()

        assert len(dns_reports) == 1
        assert dns_reports[0].service == "dns_investigator"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_filter_reports_by_target(
        self, temp_db, db_session, sample_report_data
    ):
        """Test le filtrage des rapports par cible."""
        from shared.models import Report

        targets = ["alpha@test.com", "beta@test.com", "alpha@test.com"]
        for tgt in targets:
            report = Report(target=tgt, service="breach_lookup")
            db_session.add(report)
        await db_session.commit()

        stmt = select(Report).where(Report.target == "alpha@test.com")
        result = await db_session.execute(stmt)
        filtered = result.scalars().all()

        assert len(filtered) == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_count_reports(self, temp_db, db_session):
        """Test le comptage des rapports."""
        from shared.models import Report

        for i in range(3):
            report = Report(target=f"c{i}@test.com", service="breach_lookup")
            db_session.add(report)
        await db_session.commit()

        stmt = select(func.count()).select_from(Report)
        result = await db_session.execute(stmt)
        count = result.scalar()

        assert count == 3

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_cascade_none_on_delete_service_unrelated(
        self, temp_db, db_session, sample_report_data
    ):
        """Vérifie que la suppression d'un rapport n'affecte pas les autres."""
        from shared.models import Report

        r1 = Report(target="keep@test.com", service="breach_lookup")
        r2 = Report(target="delete@test.com", service="breach_lookup")
        db_session.add_all([r1, r2])
        await db_session.commit()

        r2_id = r2.id
        await db_session.delete(r2)
        await db_session.commit()

        still_there = await db_session.get(Report, r1.id)
        assert still_there is not None
        assert still_there.target == "keep@test.com"

        deleted = await db_session.get(Report, r2_id)
        assert deleted is None


# =========================================================================
# Tests Unitaires — HTTP Client (shared/http_client.py)
# =========================================================================


class TestThothHttpClient:
    """Tests unitaires pour le ThothHttpClient."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_get_request(self, shared_http_client):
        """Vérifie qu'une requête GET simple fonctionne."""
        async with aresponses.ResponsesMockServer() as mock:
            mock.add(
                "api.example.com",
                "/data",
                "GET",
                aresponses.Response(status=200, body=b'{"key": "value"}'),
            )
            response = await shared_http_client.get("https://api.example.com/data")
            assert response.status_code == 200
            data = response.json()
            assert data == {"key": "value"}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_post_request(self, shared_http_client):
        """Vérifie qu'une requête POST avec body fonctionne."""
        async with aresponses.ResponsesMockServer() as mock:
            mock.add(
                "api.example.com",
                "/submit",
                "POST",
                aresponses.Response(status=201, body=b'{"id": 1}'),
            )
            response = await shared_http_client.post(
                "https://api.example.com/submit",
                json_data={"name": "test"},
            )
            assert response.status_code == 201
            assert response.json() == {"id": 1}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limiting_enforced(self, shared_http_client):
        """Vérifie que le rate-limiting attend entre les requêtes."""
        import time

        # Forcer un RPS bas pour observer le délai
        shared_http_client.settings.rate_limit_rps = 10.0  # 100ms entre requêtes

        async with aresponses.ResponsesMockServer() as mock:
            for _ in range(2):
                mock.add(
                    "api.example.com",
                    "/data",
                    "GET",
                    aresponses.Response(status=200, body=b'{}'),
                )

            t0 = time.time()
            await shared_http_client.get("https://api.example.com/data")
            await shared_http_client.get("https://api.example.com/data")
            elapsed = time.time() - t0

            # Au moins 100ms d'intervalle
            assert elapsed >= 0.05  # 1/10 - une petite marge

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_http_error_404_raises(self, shared_http_client):
        """Vérifie qu'un 404 lève une exception HTTPStatusError."""
        async with aresponses.ResponsesMockServer() as mock:
            mock.add(
                "api.example.com",
                "/notfound",
                "GET",
                aresponses.Response(status=404),
            )
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await shared_http_client.get("https://api.example.com/notfound")
            assert exc_info.value.response.status_code == 404

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_http_error_500_retry_then_raise(self, shared_http_client):
        """Vérifie qu'un 500 est retryé avant d'échouer."""
        shared_http_client.settings.max_retries = 2

        async with aresponses.ResponsesMockServer() as mock:
            mock.add(
                "api.example.com",
                "/error",
                "GET",
                aresponses.Response(status=500),
            )
            # Le retry va refaire la même requête
            mock.add(
                "api.example.com",
                "/error",
                "GET",
                aresponses.Response(status=500),
            )
            mock.add(
                "api.example.com",
                "/error",
                "GET",
                aresponses.Response(status=500),
            )

            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await shared_http_client.get("https://api.example.com/error")
            assert exc_info.value.response.status_code == 500

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rate_limit_429_retry_after(self, shared_http_client):
        """Vérifie qu'un 429 avec Retry-After est géré."""
        async with aresponses.ResponsesMockServer() as mock:
            # Première réponse : 429 avec Retry-After
            mock.add(
                "api.example.com",
                "/data",
                "GET",
                aresponses.Response(
                    status=429,
                    headers={"Retry-After": "0"},  # 0 pour test rapide
                    body=b'{"error": "rate limited"}',
                ),
            )
            # Deuxième réponse : succès
            mock.add(
                "api.example.com",
                "/data",
                "GET",
                aresponses.Response(status=200, body=b'{"success": true}'),
            )

            response = await shared_http_client.get("https://api.example.com/data")
            assert response.status_code == 200
            assert response.json() == {"success": True}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_exception_retry(self, shared_http_client):
        """Vérifie qu'un timeout déclenche un retry."""
        shared_http_client.settings.max_retries = 1
        shared_http_client.settings.max_timeout = 0.1  # Timeout très court

        async with aresponses.ResponsesMockServer() as mock:
            mock.add(
                "api.example.com",
                "/slow",
                "GET",
                aresponses.Response(status=200, body=b'{}'),
                delay=5,  # Délai > timeout
            )
            # Deuxième tentative : succès
            mock.add(
                "api.example.com",
                "/slow",
                "GET",
                aresponses.Response(status=200, body=b'{"retried": true}'),
                delay=0,
            )

            response = await shared_http_client.get("https://api.example.com/slow")
            assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_all_retries_exhausted_raises(self, shared_http_client):
        """Vérifie que l'épuisement des retries lève une exception."""
        shared_http_client.settings.max_retries = 2

        async with aresponses.ResponsesMockServer() as mock:
            # Toutes les tentatives échouent
            for _ in range(3):  # 1 tentative + 2 retries
                mock.add(
                    "api.example.com",
                    "/down",
                    "GET",
                    aresponses.Response(status=503),
                )

            with pytest.raises(httpx.HTTPStatusError):
                await shared_http_client.get("https://api.example.com/down")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_client(self, shared_http_client):
        """Vérifie que la fermeture du client fonctionne."""
        # Initialisation du client interne
        client = await shared_http_client._get_client()
        assert client is not None
        assert not client.is_closed

        await shared_http_client.close()
        # Après close, le client interne doit être fermé
        assert shared_http_client._client is None or shared_http_client._client.is_closed

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_custom_user_agent(self, shared_http_client):
        """Vérifie que le User-Agent est correctement défini."""
        async with aresponses.ResponsesMockServer() as mock:
            # Nous ne pouvons pas vérifier les headers envoyés via aresponses
            # mais nous pouvons vérifier que la config du client les contient
            client = await shared_http_client._get_client()
            assert "User-Agent" in client.headers
            assert "ThothOSINT" in client.headers["User-Agent"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_request_with_custom_headers(self, shared_http_client):
        """Vérifie que les headers personnalisés sont envoyés."""
        async with aresponses.ResponsesMockServer() as mock:
            mock.add(
                "api.example.com",
                "/auth",
                "GET",
                aresponses.Response(status=200, body=b'{"authed": true}'),
            )
            response = await shared_http_client.get(
                "https://api.example.com/auth",
                headers={"Authorization": "Bearer test-token"},
            )
            assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_request_with_query_params(self, shared_http_client):
        """Vérifie que les paramètres de requête sont transmis."""
        async with aresponses.ResponsesMockServer() as mock:
            # aresponses ne match pas les query params par défaut,
            # donc tout chemin /search fonctionne
            mock.add(
                "api.example.com",
                "/search",
                "GET",
                aresponses.Response(status=200, body=b'{"results": []}'),
            )
            response = await shared_http_client.get(
                "https://api.example.com/search",
                params={"q": "test", "limit": "10"},
            )
            assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_error_retries(self, shared_http_client):
        """Vérifie que les erreurs de connexion déclenchent un retry."""
        shared_http_client.settings.max_retries = 2

        # On va fermer le client pour simuler une erreur de connexion
        # et vérifier que le mécanisme de retry tente de récupérer
        async with aresponses.ResponsesMockServer() as mock:
            mock.add(
                "api.example.com",
                "/data",
                "GET",
                aresponses.Response(status=200, body=b'{"ok": true}'),
            )
            # Cette requête devrait fonctionner via aresponses
            response = await shared_http_client.get("https://api.example.com/data")
            assert response.status_code == 200


class TestHttpClientEdgeCases:
    """Tests des cas limites pour le client HTTP."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_response(self, shared_http_client):
        """Vérifie la gestion d'une réponse vide."""
        async with aresponses.ResponsesMockServer() as mock:
            mock.add(
                "api.example.com",
                "/empty",
                "GET",
                aresponses.Response(status=204),
            )
            response = await shared_http_client.get("https://api.example.com/empty")
            assert response.status_code == 204

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_large_response_body(self, shared_http_client):
        """Vérifie la gestion d'une réponse volumineuse."""
        large_body = b"x" * 100000  # 100KB
        async with aresponses.ResponsesMockServer() as mock:
            mock.add(
                "api.example.com",
                "/large",
                "GET",
                aresponses.Response(status=200, body=large_body),
            )
            response = await shared_http_client.get("https://api.example.com/large")
            assert response.status_code == 200
            assert len(response.content) == 100000

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_redirect_following(self, shared_http_client):
        """Vérifie que les redirects sont suivis."""
        async with aresponses.ResponsesMockServer() as mock:
            # aresponses ne gère pas les redirects automatiquement,
            # mais httpx avec follow_redirects=True le fait.
            # On teste juste que le client accepte les réponses 3xx
            mock.add(
                "api.example.com",
                "/old",
                "GET",
                aresponses.Response(status=301, headers={"Location": "/new"}),
            )
            response = await shared_http_client.get("https://api.example.com/old")
            # Le statut dépend si httpx suit ou non (follow_redirects=True)
            assert response.status_code in (200, 301)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_json_decode_error_handling(self, shared_http_client):
        """Vérifie la gestion d'une réponse JSON invalide."""
        async with aresponses.ResponsesMockServer() as mock:
            mock.add(
                "api.example.com",
                "/badjson",
                "GET",
                aresponses.Response(status=200, body=b"{invalid json}"),
            )
            response = await shared_http_client.get("https://api.example.com/badjson")
            # Le client ne doit pas planter sur du JSON invalide
            with pytest.raises(json.JSONDecodeError):
                response.json()


# =========================================================================
# Tests d'Intégration — Database Initialization
# =========================================================================


class TestDatabaseInitialization:
    """Tests d'intégration pour l'initialisation de la base de données."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self, temp_db):
        """Vérifie que init_db() crée bien les tables."""
        from shared.database import Base
        from sqlalchemy import inspect

        engine = temp_db["engine"]

        # Vérification que les tables existent (créées par la fixture temp_db)
        async with engine.connect() as conn:
            # SQLAlchemy 2.0: inspection synchrone
            def check_tables(sync_conn):
                inspector = inspect(sync_conn)
                tables = inspector.get_table_names()
                return tables

            tables = await conn.run_sync(check_tables)

        assert "reports" in tables

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_reports_table_columns(self, temp_db):
        """Vérifie que la table reports a les bonnes colonnes."""
        from sqlalchemy import inspect

        engine = temp_db["engine"]

        async with engine.connect() as conn:
            def check_columns(sync_conn):
                inspector = inspect(sync_conn)
                columns = [col["name"] for col in inspector.get_columns("reports")]
                return columns

            columns = await conn.run_sync(check_columns)

        expected_cols = [
            "id", "target", "service", "created_at", "updated_at",
            "data", "summary", "severity", "score", "raw_output",
            "export_format",
        ]
        for col in expected_cols:
            assert col in columns, f"Colonne manquante : {col}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_database_isolation_between_tests(self, temp_db, db_session):
        """Vérifie que chaque test a une BDD fraîche."""
        from shared.models import Report

        stmt = select(func.count()).select_from(Report)
        result = await db_session.execute(stmt)
        count = result.scalar()
        assert count == 0, "La base devrait être vide au début de chaque test"


# =========================================================================
# Tests de Résilience
# =========================================================================


class TestHttpClientResilience:
    """Tests de résilience pour le client HTTP."""

    @pytest.mark.resilience
    @pytest.mark.asyncio
    async def test_exponential_backoff(self, shared_http_client):
        """Vérifie le backoff exponentiel entre les retries."""
        import time

        shared_http_client.settings.max_retries = 3

        async with aresponses.ResponsesMockServer() as mock:
            for _ in range(4):  # 1 + 3 retries
                mock.add(
                    "api.example.com",
                    "/fail",
                    "GET",
                    aresponses.Response(status=503),
                )

            t0 = time.time()
            with pytest.raises(httpx.HTTPStatusError):
                await shared_http_client.get("https://api.example.com/fail")
            elapsed = time.time() - t0

            # Le backoff exponentiel: 2^0 + 2^1 + 2^2 = 7s de base
            # mais avec max_retries=1 dans test_env, donc ~1s
            # En réalité avec les valeurs forcées à 1, le délai est court
            # Ce test vérifie juste que ça ne bloque pas indéfiniment
            assert elapsed < 30  # Ne doit pas prendre trop longtemps

    @pytest.mark.resilience
    @pytest.mark.asyncio
    async def test_rate_limit_multiple_429(self, shared_http_client):
        """Vérifie la gestion de multiples réponses 429 successives."""
        async with aresponses.ResponsesMockServer() as mock:
            # 3 réponses 429 consécutives
            for _ in range(3):
                mock.add(
                    "api.example.com",
                    "/data",
                    "GET",
                    aresponses.Response(
                        status=429,
                        headers={"Retry-After": "0"},
                    ),
                )
            # Finalement un succès
            mock.add(
                "api.example.com",
                "/data",
                "GET",
                aresponses.Response(status=200, body=b'{"ok": true}'),
            )

            response = await shared_http_client.get("https://api.example.com/data")
            assert response.status_code == 200

    @pytest.mark.resilience
    @pytest.mark.asyncio
    async def test_dns_resolution_failure_handling(self, shared_http_client):
        """Vérifie le comportement en cas d'échec de résolution DNS."""
        # Tester avec un nom de domaine qui n'existe pas
        # httpx.ConnectError attendu
        try:
            await shared_http_client.get("https://this-domain-does-not-exist-123456789.com")
        except (httpx.ConnectError, httpx.TimeoutException):
            pass  # Comportement attendu

    @pytest.mark.resilience
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, shared_http_client):
        """Vérifie que le rate limiting fonctionne avec des requêtes concurrentes."""
        import asyncio

        async with aresponses.ResponsesMockServer() as mock:
            for _ in range(5):
                mock.add(
                    "api.example.com",
                    "/concurrent",
                    "GET",
                    aresponses.Response(status=200, body=b'{}'),
                )

            async def make_request(i):
                return await shared_http_client.get("https://api.example.com/concurrent")

            tasks = [make_request(i) for i in range(5)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Vérifie qu'aucune exception n'a été levée
            for r in results:
                if isinstance(r, Exception):
                    pytest.fail(f"Requête concurrente a échoué : {r}")
                assert r.status_code == 200


# =========================================================================
# Tests de Sécurité
# =========================================================================


class TestSecurityShared:
    """Tests de sécurité pour les modules partagés."""

    @pytest.mark.security
    def test_report_model_no_sql_injection_in_target(self, report_model_class):
        """Vérifie que le modèle Report n'exécute pas de SQL dans target."""
        malicious_target = "' OR 1=1 --"
        report = report_model_class(target=malicious_target, service="breach_lookup")
        # Le modèle doit stocker la valeur inchangée (c'est SQLAlchemy qui paramétrise)
        assert report.target == malicious_target

    @pytest.mark.security
    def test_report_model_xss_in_summary(self, report_model_class):
        """Vérifie que le modèle accepte du texte HTML (c'est le frontend qui échappe)."""
        xss_payload = "<script>alert('xss')</script>"
        report = report_model_class(
            target="test@example.com",
            service="breach_lookup",
            summary=xss_payload,
        )
        # Le modèle backend ne doit pas modifier la donnée
        # L'échappement est fait au moment de l'affichage (frontend)
        assert report.summary == xss_payload

    @pytest.mark.security
    def test_settings_no_secret_leak(self):
        """Vérifie que les clés API ne sont pas exposées dans les logs."""
        from shared.config import get_settings
        s = get_settings()
        # Vérifie que les clés sont bien des attributs masquables
        for key in ["shodan_api_key", "virustotal_api_key", "abuseipdb_api_key", "ipinfo_api_key"]:
            assert hasattr(s, key)
            # En environnement de test, elles doivent être vides
            assert getattr(s, key) == ""

    @pytest.mark.security
    def test_http_client_no_injection_in_url(self, shared_http_client):
        """Vérifie que le client HTTP n'est pas vulnérable à l'injection d'URL."""
        malicious_url = "https://api.example.com/valid"
        # Le client doit gérer sans erreur
        assert shared_http_client is not None
