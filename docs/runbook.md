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

## Activer le suivi des coûts par équipe

Le [template du budget](../templates/budget-equipe.yaml) prévoit une alerte à 80 % et filtre les frais par projet et par équipe. Activer les tags de facturation `Projet` et `Equipe` côté compte de gestion. Déployer la stack dans `us-east-1` avec le montant USD validé pour 150 CHF et une adresse de réception autorisée, puis vérifier que la vue de coûts expose les lignes correspondantes. [Filtres Budgets AWS](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-create-filters.html)
