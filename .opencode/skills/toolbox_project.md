---
name: thoth-toolbox-project
description: Comprendre le projet Projet_Thoth, sa structure modulaire, ses epics, ses rôles IA autonomes et ses critères de validation automatique.
compatibility: opencode
metadata:
  audience: thoth-toolbox-team
  workflow: autonomous-scrum
---

# Skill Thoth Toolbox Project

## What I Do

Donner le contexte projet minimal, stable et fiable pour toute décision automatique de planification, développement, test, audit de sécurité ou intégration GitHub.

## When To Use

Utiliser cette skill avant chaque étape du pipeline autonome pour s'assurer du respect des règles du projet, des scopes et de la cohérence de la Toolbox.

## Source Of Truth

- `opencode.jsonc` (Configuration globale et pipeline)
- `AGENTS.md` (Cartographie de l'équipe et des rôles)
- `documents/` (Spécifications fonctionnelles et techniques)
- `product/backend/` (Code source serveur)
- `product/frontend/` (Code source client)

## MVP Scope

Le MVP démontre une Toolbox logicielle modulaire automatisée : design unifié, architecture Front/Back, tests automatisés systématiques, conformité sécurité OWASP et livraison CI/CD autonome sur le dépôt GitHub.

Hors périmètre initial : Intégrations tierces complexes, déploiement Cloud multi-tenant, fonctionnalités hors User Story validée par le Scrum Master.

## Rôles Projet (IA)

- Scrum Master AI : Cadre Agile, validation autonome (Auto-Approval), orchestration et intégration GitHub.
- UI/UX Designer Agent : Graphisme, Design System, styles CSS et Tailwind.
- CyberSecurity Specialist Agent : Menaces en amont, audit SAST en aval, tags de sécurité.
- QA Automation Engineer Agent : Plans de tests et exécution obligatoire des 4 niveaux de tests.
- Backend Developer Agent : Logique métier, API, schémas de données et persistance.
- Frontend Developer Agent : Interface utilisateur, composants UI et intégration asynchrone des API.

## Workflow Global Autonome

1. Découper la User Story reçue de l'utilisateur.
2. Concevoir le design et valider l'architecture de sécurité en amont.
3. Rédiger le plan de test (Unitaires, Intégration, Fonctionnels, Non-régression).
4. Développer le Frontend et le Backend de manière isolée ou parallèle.
5. Exécuter la suite de tests (Exige `[STATUT: PASSED]`).
6. Réaliser l'audit de sécurité final (Exige `[SÉCURITÉ: CONFORME]`).
7. Générer la Pull Request et fusionner automatiquement sur `main`.

## Definition Of Done Projet

- Fonctionnalité implémentée sans régression.
- Style conforme au Design System de la Toolbox.
- Les 4 niveaux de tests exécutés avec succès.
- Code source audité et validé à 100% sans faille de sécurité.
- Intégration et Merge réalisés de manière autonome sur GitHub.

## Constraints

- Ne jamais outrepasser l'étape des tests ou de la sécurité.
- Ne jamais coder de secrets ou clés d'API en clair.
- Ne jamais mentionner d'IA comme auteur, source ou origine dans les livrables Git/GitHub.

## Output Format

Toujours restituer : outil de la toolbox concerné, sous-agent assigné, statut de la validation intermédiaire, risques et étape suivante du pipeline.