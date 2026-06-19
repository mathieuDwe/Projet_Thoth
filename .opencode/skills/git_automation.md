---
name: thoth-git-automation
description: Gérer de manière autonome les interactions Git et l'API GitHub pour le Projet_Thoth à l'aide du GITHUB_TOKEN d'environnement.
compatibility: opencode
metadata:
  audience: scrum-master-ai
  workflow: git-ci-cd
---

# Skill Git Automation

## What I Do

Fournir à l'agent Scrum Master les capacités techniques pour cloner, créer des branches, réaliser des commits structurés, pousser le code et interagir avec l'API GitHub de `Projet_Thoth` de manière sécurisée et invisible.

## When To Use

Utiliser uniquement à l'étape finale du pipeline autonome (Étape 8) une fois que les feux verts `[STATUT: PASSED]` et `[SÉCURITÉ: CONFORME]` ont été récoltés par les sous-agents.

## Workflow Git Autonome

1. **Checkout** : Créer une branche locale éphémère liée à la User Story (ex: `feature/us-01-password-gen`).
2. **Commit** : Rassembler les codes validés (Front, Back, Tests) et générer un commit respectant les standards humains (ex: `feat: add password generator tool to toolbox`).
3. **Push** : Envoyer la branche sur le dépôt distant `mathieuDwe/Projet_Thoth` via la variable `$GITHUB_TOKEN`.
4. **Pull Request & Merge** : Générer une Pull Request propre via l'API GitHub, appliquer les critères d'Auto-Approval et exécuter le Merge autonome sur la branche `main`.

## Constraints

- Utiliser exclusivement la clé secrète `$GITHUB_TOKEN` injectée par OpenCode.
- Ne jamais pousser directement sur la branche `main` sans passer par une branche intermédiaire et une PR.
- Interdiction stricte d'inclure des mots comme "AI", "Bot", "Agent" ou "LLM" dans les messages de commit ou les descriptions de Pull Request.