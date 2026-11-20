# Journal DevSecOps · Léman Finance

Les captures des sprints initiaux sont consultables dans le [README](../README.md). L’historique ancien ne contient pas systématiquement les heures de mise en production et de restauration. Les champs DORA historiques ci-dessous demeurent **non mesurés**.

| Sprint | Travail et preuve réutilisable | Fréquence dev/prod | Délai commit → prod | Échecs de changement | MTTR |
| --- | --- | --- | --- | --- | --- |
| 1 | VPC et plan d’adressage vérifiés dans la console | — | — | — | — |
| 2 | Routes et correction d’une route manquante | — | — | — | — |
| 3 | Filtrage SG et NACL, résultats de refus | — | — | — | — |
| 4 | Network Firewall, journal de rejet et réutilisation de l’Elastic IP | — | — | — | — |
| 5 | VPC Peering et test de non-transitivité | — | — | — | — |
| 6 | Transit Gateway et perte/restauration de propagation | — | — | — | — |
| 7 | VPN provisionnés, filtrage et bascule simulés | — | — | — | — |
| 8 | Direct Connect Gateway, choix du chemin dans la maquette BGP | — | — | — | — |
| 9 | ALB HTTPS et cible de secours, une expiration par essai | — | — | — | — |
| 10 | Route 53 privé, failover DNS et nouveau domaine public | — | — | — | — |
| 11 | Cache CloudFront, API hors cache et origine HTTPS protégée | — | — | — | — |
| 12 | Alarme CloudWatch, notification SNS et retour à OK | — | — | — | — |
| 13 | Change set, drift, recréation, préparation de la chaîne DevSecOps | Voir la session finale | En attente de promotion | Voir la session finale | Voir la session finale |

## Session finale

La chaîne vérifie la cohérence des templates, le code, les règles IaC, l’analyse des secrets, les dépendances, le SBOM et SonarQube. Les contrôles de déploiement et de qualité distinguent la [variante de quota](adr/002-quota-dev.md) de la voie EC2. Les résultats versionnés sont dans [preuves](preuves/).

| Indicateur | Mesure pendant la session |
| --- | --- |
| Fréquence de déploiement | Deux déploiements réussis de la variante Lambda en dev, dont la reconstruction. Zéro promotion en prod. |
| Délai commit → prod | Indisponible en l’absence de promotion. |
| Échecs de changement | Deux tentatives avec portail EC2 ont déclenché un rollback, sur quota VPC puis vCPU. Les deux opérations Lambda ont été vérifiées. |
| MTTR | Indisponible en l’absence d’incident prod chronométré. |

Pour ajouter les prochaines mesures DORA, utiliser les heures effectives des déploiements GitHub pour la fréquence et le délai, les déploiements ayant nécessité un correctif pour le taux d’échec, et les horodatages de l’alarme et du retour à la normale pour le MTTR. L’exercice de reconstruction mesure un RTO de lab distinct.
