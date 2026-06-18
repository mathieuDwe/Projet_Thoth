---
description: Force l'Agent Tester à exécuter les 4 niveaux de tests automatisés sur le code généré.
agent: tester_agent
---

Exécute et vérifie la suite de tests pour :

$ARGUMENTS

Lance l'exécution des tests unitaires, d'intégration, fonctionnels et de non-régression sur le code localisé dans `product/`. Renvoie le log d'exécution et termine impérativement par le tag de verdict.

## Exemple d'utilisation

```text
/run-pipeline-tests Exécuter les 4 niveaux de tests pour l'outil Générateur de mots de passe