# 🧰 Projet Thoth — AI-Managed Software Toolbox

Bienvenue sur le **Projet Thoth**, une boîte à outils (Toolbox) logicielle modulaire dont le cycle de conception, de développement, de test et d'intégration est entièrement piloté de manière autonome par une équipe d'agents IA via le framework **OpenCode**.

---

## 🚀 Vision du Projet

Le Projet Thoth a pour but de centraliser des micro-outils web utiles au quotidien (générateurs, convertisseurs, utilitaires de sécurité) au sein d'une architecture unifiée **Frontend (React/Tailwind)** et **Backend (Python/FastAPI)**. 

La particularité absolue de ce dépôt est qu'il est **auto-développé** : un orchestrateur Agile (Scrum Master) reçoit les objectifs utilisateurs, planifie les Sprints, et distribue le travail à des sous-agents IA spécialisés jusqu'à la livraison finale sur GitHub.

---

## 🤖 L'Équipe d'Agents (Gouvernance)

L'ingénierie du projet est confiée à 5 sub-agents managés par 1 orchestrateur principal. Leurs rôles et directives strictes sont cartographiés dans le fichier `.opencode/agents/AGENTS.md`.

* **Scrum Master (`scrum-master`)** : Chef de projet technique. Il gère le backlog, ordonnance le pipeline et réalise les fusions (merges) autonomes sur la branche `main` via GitHub API.
* **UI/UX Designer (`graphic-designer`)** : Responsable du Design System, de l'ergonomie visuelle et des spécifications de style CSS/Tailwind.
* **CyberSecurity Engineer (`cybersec-engineer`)** : Auditeur DevSecOps. Il réalise le Threat Modeling en amont et l'analyse statique du code (SAST) en aval. Exige le tag `[SÉCURITÉ: CONFORME]`.
* **QA Tester (`qa-tester`)** : Ingénieur qualité. Il écrit et valide obligatoirement 4 niveaux de tests (Unitaires, Intégration, Fonctionnels, Non-régression). Exige le tag `[STATUT: PASSED]`.
* **Backend Developer (`backend-dev`)** : Développeur Core. Il implémente la logique métier, les modèles de données et expose les API FastAPI.
* **Frontend Developer (`frontend-dev`)** : Intégrateur d'interface. Il conçoit les composants UI et réalise les intégrations d'API de manière asynchrone.

---

## 🔄 Le Pipeline de Développement Autonome

Chaque fonctionnalité ou outil ajouté à la Toolbox traverse obligatoirement les 8 étapes du cycle de vie OpenCode :

1. **Planning & Backlog** (`scrum-master`) $\rightarrow$ Découpage de la User Story.
2. **Visual Concept** (`graphic-designer`) $\rightarrow$ Établissement de la charte graphique de l'outil.
3. **Architecture Security Audit** (`cybersec-engineer`) $\rightarrow$ Analyse des risques en amont.
4. **Test Strategy** (`qa-tester`) $\rightarrow$ Écriture des spécifications de tests.
5. **Implementation** (`backend-dev` & `frontend-dev`) $\rightarrow$ Codage simultané ou séquentiel de l'outil.
6. **QA Validation** (`qa-tester`) $\rightarrow$ Blocage du pipeline sans le tag `[STATUT: PASSED]`.
7. **Security Inspection** (`cybersec-engineer`) $\rightarrow$ Blocage du pipeline sans le tag `[SÉCURITÉ: CONFORME]`.
8. **Deployment** (`scrum-master`) $\rightarrow$ Création automatique de la Pull Request et Merge autonome sur `main`.

---

## 📂 Structure du Dépôt

```text
PROJET_THOTH/
├── .opencode/               # Dossier de configuration de l'infrastructure IA
│   ├── agents/              # Prompts systèmes et fiches de rôles (.md)
│   ├── commands/            # Commandes système exécutables par l'IA
│   └── skills/              # Compétences et contextes avancés des agents
├── product/                 # Code source de l'application
│   ├── backend/             # Logique serveur, API FastAPI, BDD
│   └── frontend/            # Interface client React / Tailwind CSS
├── documents/               # Spécifications, cahier des charges et rapports d'audit
├── config.json              # Fichier de configuration principal OpenCode
└── README.md                # Documentation générale du projet

git clone [https://github.com/mathieuDwe/Projet_Thoth.git](https://github.com/mathieuDwe/Projet_Thoth.git)
cd Projet_Thoth

.env 
OPENCODE_MODEL=gpt-4o
OPENCODE_SMALL_MODEL=gpt-4o-mini
GITHUB_TOKEN=votre_token_d_acces_personn