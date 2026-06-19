---
description: Audite l'état actuel du code du Projet_Thoth par rapport aux exigences de la Toolbox.
agent: scrum_master
---

Audite le code existant pour :

$ARGUMENTS

Compare l'arborescence actuelle de `product/backend` et `product/frontend` avec les fichiers de spécifications. Liste ce qui est déjà opérationnel, ce qui est manquant, ainsi que les risques de structure identifiés.

## Exemple d'utilisation

```text
/audit-codebase Vérifier si l'arborescence minimale de la toolbox est présente sur main

Plaintext

/audit-codebase Comparer le dossier product/backend avec les exigences de la première User Story