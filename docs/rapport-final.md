---
title: "Léman Finance · TP final DevSecOps"
subtitle: "Synthèse de réalisation et état des validations"
date: "20 novembre 2026"
papersize: a4
geometry: "margin=19mm"
fontsize: 11pt
mainfont: "Liberation Sans"
monofont: "Liberation Mono"
colorlinks: true
linkcolor: "blue"
---

## Architecture et parcours public

Le portail de démonstration est accessible en HTTPS à l’adresse
[portail.bilelk.com](https://portail.bilelk.com/). Le parcours utilise Route 53,
CloudFront, un ALB et deux types de cibles, web et API privée. L’API, la page
d’accueil et le fichier statique ont répondu HTTP 200. Les preuves des treize
sprints et de cette mise en ligne figurent dans le
[dépôt GitHub](https://github.com/xbkh/satom-cloud-network-bko).

Le lab s’exécute à Stockholm. Les templates CloudFormation décrivent le
réseau, le calcul, le DNS, le CDN et la supervision. Les paramètres dev et
prod sont distincts. Les tests unitaires vérifient les réponses du portail,
le contenu statique, les journaux JSON et la désactivation des routes de
diagnostic dans le déploiement public.

## Qualité et gouvernance

- **8 tests réussis.** Couverture SonarQube de **94,4 %**, quality gate passé,
  0 duplication, 0 problème critique ou bloquant, 0 point sensible et
  notes A en fiabilité, sécurité et maintenabilité.
- **Sécurité statique.** cfn-lint, cfn-guard, contrôle du plan CIDR,
  Gitleaks, Semgrep et pip-audit. Le SBOM CycloneDX décrit le portail qui
  s’appuie sur la bibliothèque standard de Python.
- **GitHub.** La chaîne a vérifié le code et obtenu une session AWS
  temporaire pour dev grâce à OIDC, sans clé stockée. La branche principale
  et l’environnement prod exigent une revue indépendante.
  [Résultats GitHub Actions](https://github.com/xbkh/satom-cloud-network-bko/actions/runs/44767869440)

## Mesures en dev

Le compte partagé a refusé un nouveau VPC et de nouvelles instances EC2.
Trois sous-réseaux dédiés dans le VPC dev ont accueilli la variante
temporaire ALB interne et Lambda. Le tableau présente les mesures de
la sonde dans le VPC.

| Test | Résultat |
|:---|---:|
| Requêtes lues à débit borné | 60 |
| Taux d’erreur HTTP | 0 % |
| Latence p95 | 37,16 ms |
| Latence p99 | 49,17 ms |
| Résolution DNS interne | 49,33 ms |
| Route de diagnostic | HTTP 404 |

Les latences mesurent le trajet de la sonde vers l’ALB interne avec sa cible
Lambda, y compris la récupération de la réponse. Les chiffres sont propres
au débit de 5 requêtes/s, à Stockholm, pendant cet essai.
CloudWatch mesure aussi le délai de réponse de la cible sur une minute,
avec un p95 de 31,74 ms et un p99 de 265,28 ms.

\newpage

## Exploitation et reprise

Le module 12 a démontré une notification SNS reçue via SQS, le retour de
l’alarme à OK et la présence de flux refusés dans les journaux réseau.
La validation Lambda a consigné 64 événements JSON dans CloudWatch et
la fonction était configurée avec les traces actives.
Le runbook décrit la recherche des erreurs 5xx et les vérifications après
reconstruction. La session finale a retiré et recréé les sous-réseaux
temporaires, l’ALB et les fonctions dans le VPC dev existant.

**RTO de la variante dev de 27 min 17 s.** La mesure démarre juste avant
la suppression et s’arrête après vérification des réponses de l’accueil,
de l’API et de la route de diagnostic. AWS a passé environ vingt minutes
à libérer les interfaces réseau de la sonde. Un RPO métier demande un
scénario avec des données persistantes à restaurer. Ce portail de test
sert uniquement des réponses générées et une image.
Les deux stacks temporaires ont été supprimées après l’essai. Le
portail public répondait toujours en HTTPS lors du contrôle suivant.

## Écarts à la validation finale

| Domaine | État et dépendance |
|:----------------|:--------------------------------------------------------|
| Déploiement complet | Chemin EC2 et charge k6 à exécuter dès qu’un quota suffisant est disponible. Les tests Lambda constituent une dérogation documentée. |
| Sécurité dynamique | Sonde HTTP dans le VPC. ZAP passif local sur trois routes, 0 alerte élevée, 1 faible liée au serveur de test. Baseline ZAP dans le VPC à valider. |
| Sécurité du compte | Security Hub, AWS Config et GuardDuty absents à Stockholm. Le budget est préparé en IaC. Le score CIS et le budget demandent l’intervention du gestionnaire. |
| DNS et CDN | DNSSEC et WAF préparés en IaC et à qualifier. OAC absent. Cache confirmé par en-tête. Série mensuelle et score Lighthouse indisponibles. |
| Disponibilité | Le test de charge mesure une courte période. La disponibilité mensuelle et les SLO dans la durée restent à qualifier. |
| Connectivité des bureaux | Tunnels VPN AWS DOWN avec les adresses fictives. La redondance et BGP ont été validés sur une maquette. |
| Rendu et prod | Pull request à relire, dépôt de rendu à confirmer avec le formateur, puis promotion sous approbation humaine. |

Le journal conserve les preuves historiques et marque les mesures DORA
manquantes. Le dépôt comprend les paramètres, scripts, politiques,
captures, exports d’outils et décisions d’architecture qui accompagnent
ce rapport. [Cahier des charges](https://hackmd.io/@Formateur/rJOiAHwCMg)

**Repères.** L’IaC décrit l’infrastructure dans des fichiers. L’ALB
répartit les requêtes. Le SBOM est l’inventaire des composants logiciels.
Le RTO mesure le temps nécessaire pour remettre le service en marche.
Le RPO indique la quantité de données qu’on peut perdre lors d’une panne.
