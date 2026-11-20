# ADR 002 · Validation dev sous contrainte de quotas

**Constat.** CloudFormation a d’abord refusé un nouveau VPC, puis les nouvelles instances ont été refusées avec un plafond régional de 48 vCPU. Le compte de cours est partagé.

**Décision.** Réserver trois nouvelles plages dans le VPC dev du projet. La variante temporaire utilise un ALB interne, une cible Lambda qui reprend les routes du portail et une sonde Lambda dans le même VPC. Le groupe de sécurité n’ouvre l’ALB qu’à cette sonde. La sonde vérifie trois routes connues et limite la charge à 60 requêtes et 5 requêtes par seconde.

**Effet sur les mesures.** Les résultats décrivent ALB et Lambda dans dev. La charge k6 et la reprise d’instances EC2 restent à vérifier lorsque le compte dispose de capacité. Les ressources de test sont supprimées à la fin de la session. Le VPC réutilisé est géré par sa stack de référence.

## Validation EC2 avec le quota Spot

Le relevé suivant confirme 48 vCPU à la demande utilisés sur 48. Le quota Spot est distinct. Au moment du relevé, 4 vCPU Spot étaient utilisés sur 32. Les paramètres de dev sélectionnent désormais Spot pour les trois cibles EC2 et la sonde SSM. Les instances Spot peuvent être interrompues par AWS. Le test temporaire les supprime après exécution, y compris en cas d’échec. La configuration prod conserve la capacité à la demande. [Relevé de quota](../preuves/quota-spot.json)
