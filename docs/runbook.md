# Runbook · erreur 5xx et contrôle après reconstruction

## Alarme 5xx sur la cible du portail

1. Dans CloudWatch, relever l’heure du passage à `ALARM`, le nom de l’ALB et la métrique `HTTPCode_Target_5XX_Count`. Vérifier aussi les erreurs émises par l’ALB, qui sont comptées séparément.
2. Contrôler `/api/health`, les cibles et `HealthyHostCount`. Si seules les réponses applicatives échouent, comparer les journaux de l’application et le changement déployé.
3. Pour un accès qui expire, vérifier le listener, la règle `/api/*`, le groupe de sécurité de la cible et les flux `REJECT` liés à l’IP et au port concernés.
4. Réappliquer la version validée si le changement est en cause. Confirmer la réponse 200, le retour des cibles à `healthy`, l’état `OK` de l’alarme et la notification. Noter les deux heures.

La [preuve SNS vers SQS](../modules/12-supervision/03-alarme-sns.png) et la [preuve de retour à OK](../modules/12-supervision/05-retour-ok.png) proviennent du lab initial.

## Reconstruire dev

Le chemin EC2 utilise `bash scripts/stack.sh dev`, puis `bash scripts/verifier-dev.sh` avec une sonde SSM et la charge k6. Il dépend du profil de sonde et du quota EC2. La [variante Lambda](adr/002-quota-dev.md) utilise le script `scripts/dev-lambda.sh`. Les deux chemins visent les seules stacks de test nommées. Le chronométrage débute avant le retrait et s’arrête quand la sonde reproduit les résultats attendus. L’application de démonstration est sans état métier persistant.

Lors du test, [la reprise](preuves/reprise-dev.json) a pris 27 min 17 s, dont environ vingt minutes pour libérer les interfaces réseau de la sonde. CloudFormation attend leur suppression avant de retirer les ressources qui en dépendent. [Comportement Lambda VPC dans CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-lambda-function-vpcconfig.html)

La reprise par EC2 Spot a pris 11 min 48 s, relance CI comprise. Le workflow GitHub `Chaîne DevSecOps` avec la cible `dev` crée les stacks, lance la sonde et les retire après le test. Le [plan ZAP passif](../tests/zap-passif-dev.yaml) cible trois réponses à travers le transfert SSM de la sonde, sur le port local 18741. [Résultats Spot](preuves/reprise-spot.json)

## Activer le suivi des coûts par équipe

Le [template du budget](../templates/budget-equipe.yaml) prévoit une alerte à 80 % et filtre les frais par projet et par équipe. Activer les tags de facturation `Projet` et `Equipe` côté compte de gestion. Déployer la stack dans `us-east-1` avec le montant USD validé pour 150 CHF et une adresse de réception autorisée, puis vérifier que la vue de coûts expose les lignes correspondantes. [Filtres Budgets AWS](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-create-filters.html)

## Qualifier les protections du portail

Déployer le [WAF CloudFront](../templates/waf-cloudfront.yaml) dans `us-east-1` avec le mode observation. Utiliser la sortie `WebAclArn` dans le paramètre `CloudFrontWebAclArn` d’une distribution de dev. Comparer les métriques WAF aux réponses normales avant approbation du blocage. [Ressource AWS WAF](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-wafv2-webacl.html)

Pour les journaux réseau, donner au service CloudWatch Logs régional l’accès à la clé KMS pour le log group du projet, puis fournir l’ARN de cette clé dans `FlowLogsKeyArn`. Tester ensuite l’alarme avec `AlarmPeriodSeconds=60` et relever le délai entre les premières erreurs et la notification SQS. [Chiffrement des journaux CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/encrypt-log-data-kms.html)

Le test isolé utilise `LEMAN_DEV_ALARM=true` pour activer les diagnostics le temps de créer le lab dev. Exécuter ensuite [la vérification d’alarme](../scripts/verifier-alarme-dev.sh). Elle crée sa file et son topic dédiés, injecte des réponses 5xx depuis la sonde, mesure la réception et retire la stack de supervision. Retirer le portail de test et la sonde en fin de session. [Mesure obtenue](preuves/alarme-dev.json)

Pour DNSSEC, le [template de signature](../templates/dnssec-route53.yaml) prend l’identifiant de la zone déléguée et une clé KMS asymétrique de signature configurée à `us-east-1`. Déployer d’abord sur une zone de test. Publier le DS dans la zone parente après vérification de la signature, puis contrôler la chaîne depuis un résolveur validant. Pour retirer la signature, enlever d’abord le DS côté parent et attendre l’expiration de son cache. [Procédure AWS DNSSEC](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-configuring-dnssec.html)

### Préparer l’origine statique privée

Utiliser le [template CloudFront](../cloudformation/11-cloudfront.yaml) avec `StaticOriginMode=prepare-s3` et l’ARN de la clé KMS de la région du bucket. Le bucket bloque les accès publics et sa politique autorise seulement la distribution à lire les objets sous `static/`. Dans la politique KMS, accorder au service CloudFront le déchiffrement limité à l’ARN de cette distribution. Déposer le PNG du portail dans `static/logo.png` sur le bucket de sortie `StaticBucketName`. Passer à `StaticOriginMode=s3` après préparation, puis vérifier l’image via CloudFront et le refus d’un accès S3 anonyme. Le mode `prepare-s3` remet le trafic statique sur l’ALB tout en gardant le bucket pour un retour arrière. [Procédure AWS OAC et SSE-KMS](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)

Le paramètre `EnableCacheMetrics` permet de publier `CacheHitRate` dans CloudWatch après validation du coût. [Métriques CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/programming-cloudwatch-metrics.html)
