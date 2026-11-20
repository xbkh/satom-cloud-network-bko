---
title: "Léman Finance · TP final DevSecOps"
subtitle: "Synthèse de réalisation et état des validations"
date: "20 novembre 2026"
papersize: a4
geometry: "margin=19mm"
fontsize: 10pt
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

- **10 tests réussis.** Couverture SonarQube de **96,1 %**, quality gate passé,
  0 problème critique ou bloquant, 0 point sensible et
  notes A en fiabilité, sécurité et maintenabilité.
- **Sécurité statique.** cfn-lint, cfn-guard, contrôle du plan CIDR,
  Gitleaks, Semgrep et pip-audit. Le SBOM CycloneDX décrit le portail qui
  s’appuie sur la bibliothèque standard de Python.
- **Lighthouse.** L’accueil HTML obtient 100 en performance et 100 en
  accessibilité sur l’ALB de dev et à la médiane de trois audits GitHub.
- **GitHub.** La chaîne a vérifié le code et obtenu une session AWS
  temporaire pour déployer et vérifier dev grâce à OIDC, sans clé stockée.
  La branche principale et l’environnement prod exigent une revue indépendante.
  [Résultats GitHub Actions](https://github.com/xbkh/satom-cloud-network-bko/actions/runs/44784364625)

## Mesures en dev

Le quota à la demande est saturé. Le quota Spot distinct a permis de
lancer trois cibles EC2 et leur sonde dans le VPC dev existant. GitHub a
lancé le test k6 depuis la sonde, à 5 requêtes/s sur 20 secondes.

| Test | Résultat |
|:---|---:|
| Requêtes lues à débit borné | 101 |
| Taux d’erreur HTTP | 0 % |
| Latence p95 | 37,67 ms |
| Latence p99 | 78,98 ms |
| Résolution DNS interne | 75,62 ms |
| Route de diagnostic | HTTP 404 |

Les latences de la sonde couvrent l’aller-retour HTTP. CloudWatch mesure
le temps de réponse des cibles sur deux points d’une minute, avec un p95
maximal de 2,05 ms et un p99 maximal de 2,48 ms. Le premier essai Lambda
avait traité 60 requêtes sans erreur.

\newpage

## Exploitation et reprise

L’alarme de dev a détecté les réponses 5xx de la cible EC2. La notification
SNS est arrivée dans SQS au bout de **4 min 16 s**. Le module 12 avait déjà
montré le retour à OK et des flux refusés dans les journaux réseau.
La validation Lambda a consigné 64 événements JSON dans CloudWatch et
la fonction était configurée avec les traces actives.
**RTO EC2 Spot de 11 min 48 s.** La mesure commence à la suppression de
la stack du portail d’alarme et s’arrête au premier HTTP 200 de l’API
recréée. Elle inclut une relance GitHub. La reconstruction Lambda
précédente avait pris 27 min 17 s. Ce portail de test sert des réponses
générées et une image, sans données métier à restaurer.
Les ressources temporaires ont été retirées et le portail public a
répondu en HTTPS après nettoyage.

## Écarts à la validation finale

| Domaine | État et dépendance |
|:----------------|:--------------------------------------------------------|
| Déploiement prod | Dev est validé sur EC2 Spot. La capacité à la demande et l’approbation de prod restent à confirmer. |
| Sécurité dynamique | ZAP passif sur trois routes de l’ALB de dev via SSM. Deux alertes faibles corrigées, zéro alerte au second test. |
| Sécurité du compte | Security Hub, AWS Config et GuardDuty absents à Stockholm. Le budget est préparé en IaC. Le score CIS et le budget demandent l’intervention du gestionnaire. |
| DNS et CDN | DNSSEC, WAF et OAC en IaC, à qualifier. Dix réponses sur dix issues du cache pour l’image publique. Série mensuelle indisponible. |
| Disponibilité | Le test de charge mesure une courte période. La disponibilité mensuelle et les SLO dans la durée restent à qualifier. |
| Connectivité des bureaux | Tunnels VPN AWS DOWN avec les adresses fictives. La redondance et BGP ont été validés sur une maquette. |
| Rendu | Accès au dépôt de formation et revue indépendante à obtenir avant promotion. |

Le journal conserve les preuves historiques et marque les mesures DORA
manquantes. Le dépôt comprend les paramètres, scripts, politiques,
captures, exports d’outils et décisions d’architecture qui accompagnent
ce rapport. [Cahier des charges](https://hackmd.io/@Formateur/rJOiAHwCMg)

**Repères.** L’IaC décrit l’infrastructure dans des fichiers. L’ALB
répartit les requêtes. Le SBOM est l’inventaire des composants logiciels.
Le RTO mesure le temps nécessaire pour remettre le service en marche.
Le RPO indique la quantité de données qu’on peut perdre lors d’une panne.
