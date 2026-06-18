# Rapport d'Audit de Sécurité — Projet Thoth (Plateforme OSINT)

**Date :** 6 juin 2026  
**Auditeur :** Cybersec Engineer  
**Périmètre :** Architecture complète (4 microservices FastAPI, frontend React, configuration OpenCode, Docker, Nginx)  
**Méthodologie :** SAST (Static Application Security Testing), Threat Modeling OWASP, analyse des secrets et configuration review.

---

## Table des matières

1. [Résumé Exécutif](#1-résumé-exécutif)
2. [Analyse des Risques (Threat Modeling)](#2-analyse-des-risques-threat-modeling)
3. [Vulnérabilités Identifiées](#3-vulnérabilités-identifiées)
4. [Exposition des Secrets](#4-exposition-des-secrets)
5. [Problèmes de Configuration](#5-problèmes-de-configuration)
6. [Recommandations d'Anonymisation](#6-recommandations-danonymisation)
7. [Checklist de Sécurisation du Code](#7-checklist-de-sécurisation-du-code)
8. [Protection des Endpoints API](#8-protection-des-endpoints-api)
9. [GitHub Secrets vs .env](#9-github-secrets-vs-env)
10. [Plan d'Améliorations Concrètes](#10-plan-daméliorations-concrètes)
11. [Conclusion et Tag de Validation](#11-conclusion-et-tag-de-validation)

---

## 1. Résumé Exécutif

| Domaine | Évaluation |
|---------|-----------|
| Gestion des secrets | **CRITIQUE** — Token GitHub en clair, pas de `.gitignore` racine |
| Configuration CORS | **ÉLEVÉ** — `allow_origins=["*"]` avec `allow_credentials=True` |
| Anonymisation OSINT | **MOYEN** — Proxy optionnel, User-Agent unique et statique |
| Authentification | **CRITIQUE** — Aucune sur les endpoints API backend |
| Rate limiting | **MOYEN** — Client-side uniquement, pas de limitation distribuée |
| Dépendances | **FAIBLE** — Pas de scan CVE visible |
| Hygiène Git | **CRITIQUE** — Aucun fichier `.gitignore` à la racine du projet |

**Verdict :** La plateforme présente **8 vulnérabilités** dont **2 critiques**, **3 élevées**, **2 moyennes** et **1 faible**. Le tag `[SÉCURITÉ: CONFORME]` **ne peut pas être appliqué**.

---

## 2. Analyse des Risques (Threat Modeling)

### 2.1 Surface d'attaque

```
                    ┌─────────────────────────┐
                    │    Internet / APIs       │
                    │  (HIBP, Shodan, etc.)    │
                    └──────────┬──────────────┘
                               │ appels HTTP
                    ┌──────────▼──────────────┐
                    │  4 microservices OSINT   │
                    │  (breach_lookup, etc.)   │
                    └──────────┬──────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │      Gateway (8000)      │
                    └──────────┬──────────────┘
                               │ reverse proxy
                    ┌──────────▼──────────────┐
                    │    Nginx (port 80)       │
                    └──────────┬──────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │  Frontend React (port 3000)│
                    └─────────────────────────┘
```

### 2.2 Menaces identifiées (STRIDE par composant)

| Composant | Spoofing | Tampering | Repudiation | Info Disclosure | DoS | Elevation |
|-----------|----------|-----------|-------------|-----------------|-----|-----------|
| Gateway / Services | ID des APIs distantes | Requêtes falsifiées | Pas de logs d'audit | **Tokens API dans les réponses d'erreur** | Rate limiting faible | Pas d'auth |
| HTTP Client | Aucune validation TLS | User-Agent traçant | N/A | **Fingerprinting via header unique** | Timeouts bas | N/A |
| Frontend | Stockage localStorage | XSS via injection | N/A | **Headers CORS trop permissifs** | N/A | Token JWT inexistant |
| Docker / Nginx | Pas de secret Docker | Images non scannées | N/A | Debug exposé (`--reload`) | Aucun rate limit WAF | Ports ouverts |

### 2.3 Risques métier (OSINT)

1. **Exposition de l'analyste** : User-Agent `ThothOSINT/1.0` permet un fingerprinting certain par toutes les APIs contactées.
2. **Fuite de métadonnées** : L'IP du conteneur/serveur est visible de toutes les APIs distantes (pas de proxy/Tor obligatoire).
3. **Corrélation de requêtes** : Sans rotation d'IP ni User-Agent, un fournisseur d'API peut corréler toutes les requêtes d'un même analyste.
4. **Compromission des clés API** : Un `.env.example` listant les clés (Shodan, VirusTotal, AbuseIPDB, IPinfo) normalise leur présence en clair.

---

## 3. Vulnérabilités Identifiées

### 🔴 VULN-001 : Token GitHub en clair dans `.opencode/.env` **— CRITIQUE**

- **Fichier :** `.opencode/.env`
- **Description :** Un Personal Access Token GitHub valide est stocké en clair :
  ```
  GITHUB_TOKEN=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
  ```
- **Impact :** Un attaquant ayant accès au dépôt (même en lecture) peut effectuer des actions Git au nom du propriétaire du token : push sur `main`, création de releases, modification des issues, accès aux actions GitHub.
- **Remédiation immédiate :**
  1. Révoquer ce token immédiatement sur GitHub.com (Settings → Developer settings → Personal access tokens).
  2. Remplacer par une variable d'environnement injectée au runtime uniquement.
  3. Ajouter `*.env` au `.gitignore` racine.

### 🔴 VULN-002 : Absence de `.gitignore` racine **— CRITIQUE**

- **Description :** Aucun fichier `.gitignore` n'existe à la racine du projet.
- **Impact :** Tout fichier créé localement (`.env`, `*.key`, `credentials.json`, `__pycache__/`, `node_modules/`) peut être accidentellement versionné et poussé sur GitHub.
- **Remédiation :** Créer un `.gitignore` racine complet couvrant au minimum :
  ```gitignore
  # Environnement
  .env
  .env.*
  !.env.example

  # Python
  __pycache__/
  *.py[cod]
  *.egg-info/
  .venv/
  venv/

  # Node
  node_modules/
  package-lock.json

  # IDE
  .vscode/
  .idea/

  # OS
  .DS_Store
  Thumbs.db

  # Secrets
  *.key
  *.pem
  credentials.json

  # Data
  *.db
  /data/
  ```

### 🔴 VULN-003 : Absence d'authentification sur les endpoints API **— CRITIQUE**

- **Fichier :** `product/backend/services/breach_lookup/main.py` (même pattern pour tous les services)
- **Description :** Tous les endpoints sont publics :
  ```python
  @app.post("/lookup/email")      # Pas de dépendance d'auth
  @app.post("/lookup/username")   # Pas de dépendance d'auth
  @app.post("/report")            # Pas de dépendance d'auth
  ```
- **Impact :** N'importe qui peut interroger les APIs OSINT via la plateforme (vol de service, épuisement des quotas API, utilisation comme proxy open resolver).
- **Remédiation :** Implémenter un middleware d'authentification JWT ou une clé API partagée :
  ```python
  from fastapi import Depends, HTTPException, Security
  from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

  security = HTTPBearer(auto_error=False)

  async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
      if not credentials or credentials.credentials != settings.api_key:
          raise HTTPException(status_code=401, detail="Invalid or missing API key")
      return credentials.credentials
  ```

### 🟠 VULN-004 : CORS extrêmement permissif **— ÉLEVÉ**

- **Fichier :** `product/backend/services/breach_lookup/main.py` ligne 25-31
- **Code :**
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],       # ← N'importe quelle origine
      allow_credentials=True,    # ← Permet les cookies/headers d'auth
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- **Impact :** `allow_origins=["*"]` combiné avec `allow_credentials=True` est une configuration invalide selon la spécification Fetch (les navigateurs la rejettent), mais surtout, tout site web malveillant peut faire des requêtes cross-origin vers l'API.
- **Remédiation :**
  ```python
  allow_origins=settings.cors_origins.split(",") if settings.cors_origins else [],
  allow_credentials=True,
  ```
  Avec `CORS_ORIGINS=https://thoth.example.com` dans le `.env`.

### 🟠 VULN-005 : User-Agent unique et statique **— ÉLEVÉ**

- **Fichier :** `product/backend/shared/http_client.py` ligne 25
- **Code :**
  ```python
  headers={"User-Agent": "ThothOSINT/1.0 (OSINT Platform)"}
  ```
- **Impact :** Chaque requête sortante est parfaitement identifiable et traçable. Les fournisseurs d'API (HIBP, Shodan, VirusTotal) peuvent immédiatement bloquer ou fingerprint ce User-Agent. L'analyste est exposé et corrélable.
- **Remédiation :** Implémenter une rotation de User-Agents réalistes :
  ```python
  USER_AGENTS = [
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
      "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...",
  ]

  headers={"User-Agent": random.choice(USER_AGENTS)}
  ```

### 🟡 VULN-006 : Mauvais usage des clés API **— MOYEN**

- **Fichier :** `product/backend/services/breach_lookup/main.py` lignes 89, 115, 127
- **Code :**
  ```python
  headers={"hibp-api-key": settings.virustotal_api_key or ""}   # Ligne 89, 115
  api_key = settings.abuseipdb_api_key                          # Ligne 127 (pour leakcheck)
  ```
- **Impact :**
  1. HIBP nécessite sa propre clé API, pas celle de VirusTotal. Les appels HIBP échoueront silencieusement (renvoi en 401/403) et la clé VirusTotal est inutilement exposée à HIBP.
  2. Le champ `abuseipdb_api_key` est utilisé pour leakcheck.net, ce qui est un détournement sémantique dangereux. Si AbuseIPDB et leakcheck ont des formats de clé différents, les deux seront inopérants.
- **Remédiation :**
  ```python
  # Dans config.py
  class Settings(BaseSettings):
      # ...
      hibp_api_key: str = ""
      leakcheck_api_key: str = ""
  ```

### 🟡 VULN-007 : Debug mode dans les conteneurs Docker **— MOYEN**

- **Fichier :** `product/docker/docker-compose.yml`
- **Code :**
  ```yaml
  command: uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Impact :** Le flag `--reload` active le hot-reload (adapté au développement uniquement). En production, il expose des risques de redémarrage intempestif, de fuite de mémoire et de ralentissement. De plus, `--host 0.0.0.0` expose sur toutes les interfaces réseau.
- **Remédiation :** Utiliser un entrypoint de production :
  ```yaml
  command: uvicorn gateway.main:app --host 127.0.0.1 --port 8000 --workers 4
  ```

### 🟢 VULN-008 : Aucune politique de sécurité des dépendances **— FAIBLE**

- **Description :** Les dépendances dans `requirements.txt` sont épinglées à des versions spécifiques mais aucun mécanisme de scan CVE n'est en place (pas de `pip-audit`, `safety`, ou Dependabot config).
- **Remédiation :** Ajouter un workflow GitHub Actions :
  ```yaml
  - name: Scan CVEs
    run: pip-audit --requirement product/backend/requirements.txt
  ```

---

## 4. Exposition des Secrets

### 4.1 Inventaire des secrets trouvés

| Fichier | Secret | Type | Statut |
|---------|--------|------|--------|
| `.opencode/.env` | `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` | GitHub PAT | ⚠️ En clair, non versionné (mais non protégé) |
| `.env.example` | Emplacements vides pour clés API | Template | ⚠️ Normalise le stockage en clair |
| `README.md` | `GITHUB_TOKEN=votre_token_d_acces_personn` | Documentation | ⚠️ Encourage la pratique risquée |

### 4.2 Vecteurs de fuite potentiels

1. **Commit accidentel** : Si quelqu'un exécute `git add .` puis `git commit` sans `.gitignore`, `.opencode/.env` est versionné.
2. **Dump de base** : Les réponses d'erreur des APIs (non filtrées) peuvent contenir des clés dans les stack traces.
3. **Logs Docker** : Les variables d'environnement sont visibles dans `docker inspect` et `docker logs`.
4. **Image Docker** : Si les `.env` sont copiés dans l'image via `COPY . /app`, les clés sont extractibles.

---

## 5. Problèmes de Configuration

### 5.1 Infrastructure

| Problème | Détail | Sévérité |
|----------|--------|----------|
| Pas de `.gitignore` racine | Aucun fichier à la racine du projet | Critique |
| `.opencode/.gitignore` incomplet | N'ignore pas `.env` | Élevé |
| `config.json` lit `GITHUB_TOKEN` depuis l'env | Dépend d'une variable d'env sécurisée | Info |
| Pas de séparation des environnements | Même conf pour dev/prod | Moyen |

### 5.2 Docker

| Problème | Détail | Sévérité |
|----------|--------|----------|
| Ports exposés inutilement | Chaque service expose son port individuellement (8000-8004) | Moyen |
| `--reload` en production | Hot-reload actif dans docker-compose | Moyen |
| Volumes montés en mode lecture/écriture | `../backend:/app` permet la modification du code depuis le conteneur | Moyen |

### 5.3 Frontend

| Problème | Détail | Sévérité |
|----------|--------|----------|
| Proxy dev vers `localhost:8080` | `changeOrigin: true` sans validation | Faible |
| Stockage token dans localStorage | `localStorage.getItem('thoth_token')` — vulnérable au XSS | Moyen |
| Pas de CSP headers | Aucune Content Security Policy configurée | Moyen |

---

## 6. Recommandations d'Anonymisation

Pour une plateforme OSINT, l'anonymisation des requêtes sortantes n'est pas optionnelle. Voici les mesures à implémenter **obligatoirement** :

### 6.1 Proxy SOCKS5 obligatoire

```python
# http_client.py — Rendre le proxy obligatoire
class ThothHttpClient:
    def __init__(self, service_name: str = "generic"):
        self.settings = get_settings()
        if not self.settings.proxy_url:
            raise RuntimeError("PROXY_URL is mandatory for OSINT operations")
        self.proxy_url = self.settings.proxy_url
```

### 6.2 Support Tor intégré

Le `.env` devrait permettre :
```env
# Mode d'anonymisation
ANON_MODE=tor          # tor | socks5 | none (interdit en prod)
TOR_CONTROL_PORT=9051
TOR_SOCKS_PORT=9050
PROXY_URL=socks5://127.0.0.1:9050
```

### 6.3 Rotation d'IP (tor --new-circuit)

Après N requêtes, forcer un nouveau circuit Tor :
```python
async def rotate_identity():
    if self.settings.anon_mode == "tor":
        # Envoie NEWNYM au contrôle Tor
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://127.0.0.1:9051/control/new_circuit",
                auth=("", settings.tor_password),
            )
```

### 6.4 Anti-fingerprinting complet

```python
# http_client.py — Headers anti-fingerprinting
class AntiFingerprintHeaders:
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]

    ACCEPT_LANGUAGES = ["en-US,en;q=0.9", "en-GB,en;q=0.8", "fr-FR,fr;q=0.9"]

    @classmethod
    def get_headers(cls) -> dict:
        return {
            "User-Agent": random.choice(cls.USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": random.choice(cls.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "Connection": "keep-alive",
        }

    @classmethod
    def rotate(cls):
        """À appeler avant chaque requête."""
        return cls.get_headers()
```

---

## 7. Checklist de Sécurisation du Code

### 7.1 Validation des entrées ✅ Avec améliorations

**État actuel :** Partiellement correct.
- ✅ Validation des emails (regex) — `breach_lookup/main.py:48`
- ✅ Validation des usernames (caractères autorisés, longueur) — `breach_lookup/main.py:63`
- ❌ **Aucune limite de taille** sur les champs texte (risque de buffer overflow / DoS par payload volumineux)
- ❌ **Aucune sanitization HTML** dans `raw_output` — si ce champ est affiché dans le frontend, XSS possible

**À corriger :**
```python
class ReportSaveRequest(BaseModel):
    target: str = Field(..., max_length=255)
    summary: str = Field(default="", max_length=2000)
    data: dict = Field(default_factory=dict)
    # strip HTML tags from raw data
    raw_output: str = Field(default="", max_length=50000)
```

### 7.2 Rate limiting

**État actuel :** Client-side uniquement (auto-throttling).
- ❌ Pas de rate limiting par IP client
- ❌ Pas de rate limiting distribué via Redis
- ❌ Pas de backpressure sur les appels sortants

**À implémenter :**
```python
# Middleware FastAPI pour rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/lookup/email")
@limiter.limit("10/minute")
async def lookup_email(request: EmailLookupRequest):
    ...
```

### 7.3 Protection des endpoints

| Endpoint | Méthode | Protection requise | Priorité |
|----------|---------|-------------------|----------|
| `/health` | GET | Aucune (utile pour les healthchecks) | Faible |
| `/lookup/email` | POST | Auth + Rate limit + Validation | Haute |
| `/lookup/username` | POST | Auth + Rate limit + Validation | Haute |
| `/report` | POST | Auth + Rate limit + Limite de taille | Haute |

### 7.4 Headers de sécurité (Nginx)

```nginx
# À ajouter dans nginx.conf
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

---

## 8. Protection des Endpoints API

### 8.1 Architecture recommandée

```
                    ┌─────────────────────────┐
                    │    API Gateway (8000)    │
                    │  - Auth JWT vérification │
                    │  - Rate limiting Redis   │
                    │  - Audit logging         │
                    └──────┬──────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
    ┌─────────▼──┐  ┌─────▼──────┐  ┌──▼──────────┐
    │ Breach     │  │ Social     │  │ DNS / IP    │
    │ Lookup     │  │ Harvester  │  │ Geoloc      │
    └────────────┘  └────────────┘  └─────────────┘
                           │
              ┌────────────▼────────────┐
              │  Proxy SOCKS5 / Tor     │
              │  + Rotation User-Agent  │
              │  + Anti-fingerprinting  │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │  APIs externes (HIBP,   │
              │  Shodan, VirusTotal...) │
              └─────────────────────────┘
```

### 8.2 Middleware de sécurité unifié

```python
# shared/security.py — Middleware de sécurité centralisé
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import time
import hashlib
import hmac

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Vérifier l'authentification
        api_key = request.headers.get("X-API-Key")
        if not api_key or not self._verify_api_key(api_key):
            raise HTTPException(status_code=401, detail="Missing or invalid API key")

        # 2. Rate limiting par IP + clé
        client_ip = request.client.host
        if not self._check_rate_limit(client_ip, api_key):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

        # 3. Logs d'audit
        request.state.start_time = time.time()
        response = await call_next(request)

        # 4. Supprimer les headers sensibles
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)

        return response

    def _verify_api_key(self, key: str) -> bool:
        # Vérification à faire via Redis/DB avec hash
        return True  # TODO: implémenter

    def _check_rate_limit(self, ip: str, key: str) -> bool:
        # TODO: implémenter avec Redis (token bucket)
        return True
```

---

## 9. GitHub Secrets vs .env

### 9.1 Recommandation : Hybride

| Usage | Stockage | Mécanisme |
|-------|----------|-----------|
| **CI/CD (GitHub Actions)** | GitHub Secrets | `${{ secrets.SHODAN_API_KEY }}` |
| **Développement local** | `.env` local | `.gitignore` + template `.env.example` |
| **Production** | Secrets manager (HashiCorp Vault, AWS Secrets Manager, ou variables d'environnement Docker Swarm/K8s) | Injection au runtime |

### 9.2 Configuration GitHub Actions

```yaml
name: Security Scan & Deploy
on: [push, pull_request]
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Scan for secrets
        uses: trufflesecurity/trufflehog@v3
        with:
          extra_args: --results=verified,unknown

      - name: Scan dependencies for CVEs
        run: |
          pip install pip-audit
          pip-audit --requirement product/backend/requirements.txt

      - name: Run SAST
        uses: PyCQA/bandit-action@v1
        with:
          path: product/backend/
```

### 9.3 Script de vérification des secrets (pre-commit)

```bash
#!/bin/bash
# .githooks/pre-commit — Vérifie qu'aucun secret n'est commité

if git diff --cached --name-only | grep -qE '\.env$|\.key$|credentials\.json'; then
    echo "❌ ERREUR : Tentative de commit d'un fichier sensible (.env, .key, credentials)."
    exit 1
fi

# Détection de patterns de tokens dans les fichiers stagés
git diff --cached --diff-filter=A --name-only | while read file; do
    if grep -qE '(ghp_|gho_|ghu_|ghs_|ghr_)[A-Za-z0-9_]{36,}' "$file"; then
        echo "❌ ERREUR : Token GitHub détecté dans $file"
        exit 1
    fi
done
```

---

## 10. Plan d'Améliorations Concrètes

### 10.1 IMMÉDIAT (24h)

| # | Action | Responsable | Priorité |
|---|--------|-------------|----------|
| 1 | **Révoquer le token GitHub** `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` | Admin | Critique |
| 2 | Créer un `.gitignore` racine incluant `*.env` | Développeur | Critique |
| 3 | Ajouter `.env` dans `.opencode/.gitignore` | Développeur | Critique |
| 4 | Supprimer le `.env.example` du suivi ou le neutraliser | Développeur | Haute |

### 10.2 COURT TERME (1 semaine)

| # | Action | Priorité |
|---|--------|----------|
| 5 | Implémenter un middleware d'authentification JWT sur tous les endpoints | Critique |
| 6 | Remplacer le CORS `["*"]` par une liste blanche configurable | Haute |
| 7 | Corriger l'assignation des clés API (HIBP vs VirusTotal, leakcheck vs AbuseIPDB) | Haute |
| 8 | Implémenter la rotation des User-Agents | Haute |
| 9 | Ajouter un rate limiting distribué via Redis | Haute |

### 10.3 MOYEN TERME (2-4 semaines)

| # | Action | Priorité |
|---|--------|----------|
| 10 | Rendre le proxy SOCKS5 obligatoire + support Tor | Haute |
| 11 | Ajouter les headers de sécurité (CSP, HSTS, X-Frame-Options) dans Nginx | Haute |
| 12 | Mettre en place un pipeline CI/CD avec scan de secrets (TruffleHog) et CVE | Moyenne |
| 13 | Configurer Dependabot / Renovate pour les dépendances | Moyenne |
| 14 | Remplacer `--reload` par une config de production dans docker-compose | Moyenne |
| 15 | Ajouter un pré-commit hook pour la détection de secrets | Moyenne |

### 10.4 LONG TERME (1-3 mois)

| # | Action | Priorité |
|---|--------|----------|
| 16 | Implémenter le chiffrement de la base de données SQLite (via sqlcipher) | Faible |
| 17 | Ajouter un WAF (Web Application Firewall) en amont de Nginx | Faible |
| 18 | Audit de sécurité externe (pentest) | Faible |
| 19 | HSM / Vault pour la gestion centralisée des secrets | Faible |

---

## 11. Conclusion et Tag de Validation

### 11.1 Synthèse

| Catégorie | Nombre | Détail |
|-----------|--------|--------|
| 🔴 Critique | 3 | VULN-001 (token GitHub), VULN-002 (pas de .gitignore), VULN-003 (pas d'auth) |
| 🟠 Élevé | 2 | VULN-004 (CORS permissif), VULN-005 (User-Agent unique) |
| 🟡 Moyen | 2 | VULN-006 (mauvaises clés API), VULN-007 (debug mode) |
| 🟢 Faible | 1 | VULN-008 (pas de scan CVE) |

### 11.2 Tag de validation

```diff
- [SÉCURITÉ: CONFORME]
+ [SÉCURITÉ: VULNÉRABLE]
```

**Raison :** La présence de **3 vulnérabilités critiques** (token GitHub en clair, pas de `.gitignore` racine, pas d'authentification sur les endpoints) empêche l'application du tag `[SÉCURITÉ: CONFORME]`. Conformément aux règles de l'agent Cybersec Engineer : *"Ne Pas Utiliser Pour — Valider le code si une vulnérabilité de niveau Moyen, Élevé ou Critique est présente."*

### 11.3 Prochaines étapes

1. Appliquer les corrections **IMMÉDIATES** (section 10.1).
2. Après correction des 3 vulnérabilités critiques, demander un **ré-audit** complet.
3. Le tag `[SÉCURITÉ: CONFORME]` pourra être appliqué uniquement après :
   - Révocation et remplacement du token GitHub
   - Création du `.gitignore` racine
   - Implémentation de l'authentification sur tous les endpoints
   - Correction des assignations de clés API
   - Implémentation de la rotation des User-Agents
   - Durcissement du CORS

---

*Rapport généré par l'agent Cybersec Engineer. Les corrections immédiates sont à appliquer avant tout nouveau commit sur la branche `main`.*

`[SÉCURITÉ: VULNÉRABLE]`
