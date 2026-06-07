# Stratégie de Test — Plateforme OSINT Thoth

**Version :** 1.0  
**Date :** 2026-06-06  
**Responsable :** QA Engineer  
**Statut :** Approuvé  

---

## 1. Objectif

Garantir la robustesse, la fiabilité et la sécurité de la plateforme OSINT Thoth à travers **4 niveaux de tests obligatoires** pour chacun des 4 microservices, le Gateway et les modules partagés.

---

## 2. Architecture Cible

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Frontend   │────▶│   Gateway    │────▶│  breach_lookup   │
│  (React)    │     │  (port 8000) │     │  (port 8001)     │
└─────────────┘     └──────────────┘     ├──────────────────┤
                                         │ social_harvester │
▲  Tests E2E        ▲ Tests              │ (port 8002)      │
│  (Cypress/Play)   │ Intégration        ├──────────────────┤
│                   │                    │ dns_investigator │
│                   │                    │ (port 8003)      │
│                   │                    ├──────────────────┤
│                   │                    │ ip_geoloc        │
│                   │                    │ (port 8004)      │
│                   │                    └──────────────────┘
│                   │
│  ┌─────────────────────────────────────────────┐
│  │           Shared Modules                    │
│  │  (database.py, models.py, http_client.py,  │
│  │           config.py)                        │
│  └─────────────────────────────────────────────┘
│
└── Tests Unitaires (validation isolée)
```

---

## 3. Niveaux de Test

### 3.1 Tests Unitaires (Niveau 1)

**Objectif :** Validation isolée de chaque fonction et composant.

| Couche | Éléments testés | Outil |
|--------|----------------|-------|
| **Shared** | `http_client.ThothHttpClient` (requêtes, rate limiting, retry, timeout) | pytest + aresponses |
| **Shared** | `models.Report` (création, sérialisation, validation) | pytest |
| **Shared** | `database` (session, CRUD) | pytest-asyncio |
| **Shared** | `config.Settings` (validation, valeurs par défaut) | pytest |
| **Services** | Fonctions métier de chaque microservice | pytest + aresponses |
| **Gateway** | Routage, agrégation, cache | pytest + aresponses |

**Règle :** Les mocks sont autorisés uniquement pour les appels externes (APIs tierces, HTTP). Le code métier interne ne doit pas être mocké.

### 3.2 Tests d'Intégration (Niveau 2)

**Objectif :** Validation des interactions entre les couches.

| Scénario | Description |
|----------|-------------|
| **Gateway → Service** | Vérifier que le gateway achemine correctement vers chaque microservice |
| **Service → Base de données** | CRUD complet des rapports via SQLite |
| **Service → HTTP Externe** | Validation des appels avec httpx (mode live ou replay) |
| **Frontend → API** | Vérifier que les appels frontend aboutissent (contrats OpenAPI) |

**Règle :** Base de données SQLite de test isolée (`test_thoth.db`). Les appels externes doivent être replayés via des fixtures VCR ou aresponses.

### 3.3 Tests Fonctionnels (Niveau 3)

**Objectif :** Scénarios complets de bout en bout.

| Scénario | Flux |
|----------|------|
| **Scan complet d'une cible** | Frontend → Gateway → Microservice (avec résultat réel ou simulé) → Sauvegarde BDD → Affichage rapport |
| **Génération de rapport PDF** | API → Export PDF → Téléchargement |
| **Liste des rapports** | API GET /reports → Filtrage → Pagination |
| **Suppression de rapport** | API DELETE /reports/{id} → Vérification BDD |

### 3.4 Tests de Non-Régression (Niveau 4)

**Objectif :** Vérifier que les outils existants fonctionnent après chaque modification.

**Procédure :**
1. Exécuter la suite complète de tests unitaires de tous les services.
2. Exécuter la suite d'intégration.
3. Comparer les résultats avec le rapport précédent.
4. Tout écart = blocage pipeline.

---

## 4. Cas de Test par Microservice

### 4.1 Service : `breach_lookup` (Port 8001)

| ID | Type | Cas | Résultat attendu |
|----|------|-----|------------------|
| BL-U1 | Unitaire | Vérifier la validation d'email | 422 si email invalide |
| BL-U2 | Unitaire | Vérifier le parsing de breach.json | Dictionnaire structuré |
| BL-U3 | Unitaire | Timeout API externe → retry | Exception levée après N tentatives |
| BL-I1 | Intégration | POST /api/v1/breach-lookup/scan avec email valide | 200 + rapport créé en BDD |
| BL-I2 | Intégration | GET /api/v1/breach-lookup/reports | Liste paginée |
| BL-I3 | Intégration | GET /api/v1/breach-lookup/reports/{id} | Rapport spécifique |
| BL-F1 | Fonctionnel | Scan complet → Rapport → Export PDF | PDF téléchargeable |
| BL-R1 | Résilience | Rate limiting (429) → backoff → reprise | Requête réussie après attente |
| BL-S1 | Sécurité | Injection SQL dans le paramètre email | Rejeté (422) |

### 4.2 Service : `social_harvester` (Port 8002)

| ID | Type | Cas | Résultat attendu |
|----|------|-----|------------------|
| SH-U1 | Unitaire | Validation username | 422 si username vide |
| SH-U2 | Unitaire | Parsing réponse JSON d'API sociale | Structure normalisée |
| SH-U3 | Unitaire | Gestion d'erreur API (403) | Exception avec message clair |
| SH-I1 | Intégration | POST /api/v1/social-harvester/scan | 200 + profil trouvé |
| SH-I2 | Intégration | GET /api/v1/social-harvester/reports | Liste paginée |
| SH-I3 | Intégration | GET /api/v1/social-harvester/reports/{id} | 404 si ID inexistant |
| SH-F1 | Fonctionnel | Scan username → Résultats agrégés | Rapport multi-plateforme |
| SH-R1 | Résilience | Timeout connexion API Twitter | Fallback gracieux |
| SH-S1 | Sécurité | Username avec caractères spéciaux (<script>) | Échappé / rejeté |

### 4.3 Service : `dns_investigator` (Port 8003)

| ID | Type | Cas | Résultat attendu |
|----|------|-----|------------------|
| DI-U1 | Unitaire | Validation domaine | 422 si domaine invalide |
| DI-U2 | Unitaire | Résolution DNS A/AAAA | Liste d'IPs |
| DI-U3 | Unitaire | WHOIS lookup | Informations registrar |
| DI-I1 | Intégration | POST /api/v1/dns-investigator/scan | 200 + enregistrements DNS |
| DI-I2 | Intégration | GET /api/v1/dns-investigator/reports | Liste paginée |
| DI-I3 | Intégration | DELETE /api/v1/dns-investigator/reports/{id} | 204 + suppression BDD |
| DI-F1 | Fonctionnel | Scan domaine → DNS + WHOIS → Rapport | Rapport complet |
| DI-R1 | Résilience | Serveur DNS qui ne répond pas | Timeout géré |
| DI-S1 | Sécurité | Domaine avec injection de commande | Rejeté (422) |

### 4.4 Service : `ip_geoloc` (Port 8004)

| ID | Type | Cas | Résultat attendu |
|----|------|-----|------------------|
| IP-U1 | Unitaire | Validation IP | 422 si IP invalide |
| IP-U2 | Unitaire | Parsing réponse ipinfo.io/abuseipdb | Structure normalisée |
| IP-U3 | Unitaire | Gestion quota API | Message explicite |
| IP-I1 | Intégration | POST /api/v1/ip-geoloc/scan | 200 + géolocalisation |
| IP-I2 | Intégration | GET /api/v1/ip-geoloc/reports | Liste paginée |
| IP-I3 | Intégration | PUT /api/v1/ip-geoloc/reports/{id} | Mise à jour du rapport |
| IP-F1 | Fonctionnel | Scan IP → Carte + Réputation → Rapport complet | Carte + données WHOIS |
| IP-R1 | Résilience | API ipinfo.io down | Fallback sur abuseipdb |
| IP-S1 | Sécurité | IP privée (127.0.0.1, 10.x.x.x) | Rejetée ou warning |

### 4.5 Service : `gateway` (Port 8000)

| ID | Type | Cas | Résultat attendu |
|----|------|-----|------------------|
| GW-U1 | Unitaire | Routage vers le bon service | URL correctement proxyfiée |
| GW-U2 | Unitaire | Agrégation des résultats | JSON combiné |
| GW-I1 | Intégration | GET /health | 200 + statuts de tous les services |
| GW-I2 | Intégration | POST /api/v1/scan (cible complète) | Agrégation 4 services |
| GW-F1 | Fonctionnel | Scan complet via gateway | Rapport consolidé |
| GW-R1 | Résilience | Un service down → autres réponses partielles | 200 partiel + champ "error" |
| GW-S1 | Sécurité | Header injection | Rejeté |

---

## 5. Tests de Résilience

### 5.1 Timeout
- Simuler un délai de réponse > `MAX_TIMEOUT` (30s) via aresponses.
- Vérifier que `ThothHttpClient` lève `httpx.TimeoutException` après retries.
- Vérifier que le service retourne un 504 avec message explicite.

### 5.2 Rate Limiting
- Simuler une réponse HTTP 429 (Too Many Requests) avec header `Retry-After`.
- Vérifier le backoff exponentiel + jitter.
- Vérifier que la requête réussit après l'attente.

### 5.3 Échec API Externe
- Simuler un 500, 502, 503.
- Vérifier le retry (max 3).
- Vérifier le fallback sur service alternatif (ex: ipinfo → abuseipdb).

---

## 6. Tests de Sécurité

### 6.1 Injection
| Vecteur | Exemple | Protection |
|---------|---------|------------|
| SQL | `' OR 1=1 --` | SQLAlchemy paramètres |
| NoSQL | `{ "$gt": "" }` | Validation Pydantic |
| Command | `; rm -rf /` | Rejet pattern shell |
| XSS | `<script>alert(1)</script>` | Échappement HTML |
| Header | `\r\nX-Hacked: true` | Sanitization FastAPI |

### 6.2 Validation
- Champs requis manquants → 422
- Types invalides → 422
- Tailles limites → 422 si dépassement
- Format UUID invalide → 422
- Enumérations hors limites → 422

---

## 7. Tests de Connectivité Réelle (Validation Terrain)

Ces tests nécessitent un réseau actif et des APIs externes configurées.

| ID | Service | Cible | Commande |
|----|---------|-------|----------|
| RC-1 | breach_lookup | `test@example.com` | `POST /api/v1/breach-lookup/scan` |
| RC-2 | social_harvester | `john_doe` | `POST /api/v1/social-harvester/scan` |
| RC-3 | dns_investigator | `example.com` | `POST /api/v1/dns-investigator/scan` |
| RC-4 | ip_geoloc | `8.8.8.8` | `POST /api/v1/ip-geoloc/scan` |
| RC-5 | gateway | Agrégation complète | `POST /api/v1/scan` |

**Condition :** Ces tests sont marqués `@pytest.mark.real_connectivity` et exclus de l'exécution standard. Ils sont exécutés manuellement avant mise en production.

---

## 8. Exécution des Tests

### 8.1 Commandes

```bash
# Tests unitaires uniquement
pytest -m unit -v

# Tests d'intégration
pytest -m integration -v

# Tests fonctionnels
pytest -m functional -v

# Tests de non-régression (toute la suite sauf real_connectivity)
pytest --ignore-glob='*real_connectivity*' -v

# Suite complète (hors connectivité réelle)
pytest -v --cov=services --cov=shared --cov=gateway --cov-report=term-missing

# Tests de résilience uniquement
pytest -m resilience -v

# Tests de sécurité uniquement
pytest -m security -v
```

### 8.2 Rapport de Couverture

- **Objectif :** > 85% de couverture ligne pour les services.
- **Objectif :** > 90% de couverture ligne pour les modules partagés.
- Génération : `pytest --cov --cov-report=html:documents/04_qa/reports/coverage`

---

## 9. Critères d'Acceptation

Un outil est considéré **validé** si et seulement si :

1. ✅ 100% des tests unitaires passent.
2. ✅ 100% des tests d'intégration passent.
3. ✅ 100% des tests fonctionnels passent.
4. ✅ 100% des tests de non-régression passent.
5. ✅ Tous les cas de sécurité listés sont couverts et passent.
6. ✅ La couverture de code est ≥ 85%.
7. ✅ Aucun test marqué `xfail` (sauf bugs documentés).

**Verdict :** `[STATUT: PASSED]` ou `[STATUT: FAILED]`

---

## 10. Structure des Fichiers de Test

```
product/backend/tests/
├── conftest.py                          # Fixtures globales
├── test_shared.py                       # Tests module partagé
├── test_breach_lookup.py                # Tests breach_lookup
├── test_social_harvester.py             # Tests social_harvester
├── test_dns_investigator.py             # Tests dns_investigator
├── test_ip_geoloc.py                    # Tests ip_geoloc
├── test_gateway.py                      # Tests gateway
└── reports/                             # Rapports d'exécution
    └── *.xml

product/frontend/tests/
├── ... (tests frontend à implémenter)
```
