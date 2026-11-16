# Satom Cloud Network — Groupe Léman Finance

Projet du cours AWS E3. La région du lab est Stockholm (`eu-north-1`). Les ressources sont définies dans CloudFormation et les changements sont versionnés dans Git.

Les noms de ressources prennent le suffixe `_bko`. Pour les services dont le nom interdit le caractère souligné, utiliser `-bko`, comme pour la stack CloudFormation. Les tags obligatoires du cours gardent leurs valeurs, dont le nom exact de l’équipe.

## Module 1 — TP 1

Le [template](cloudformation/01-tp1-reseau.json) crée `vpc-prod-leman_bko` et les sous-réseaux `sub-public-1a_bko` et `sub-prive-1a_bko` en zone `eu-north-1a`. Il prend le nom de l'équipe en paramètre.

**Déployé le 16 novembre 2026.** La stack `satom-leman-prod-bko` est en `CREATE_COMPLETE`. Le VPC `vpc-prod-leman_bko` utilise le CIDR `10.0.0.0/16` et les tags `Projet=SatomCloudNetwork`, `Equipe=bko` et `Environnement=prod`.

| Sous-réseau | CIDR | Zone |
|---|---|---|
| `sub-public-1a_bko` | `10.0.1.0/24` | `eu-north-1a` |
| `sub-prive-1a_bko` | `10.0.2.0/24` | `eu-north-1a` |

La table de routage principale contient une seule entrée, `10.0.0.0/16 → local`.

### Réalisation du TP 1 en captures

**1.** CloudFormation valide le template à Stockholm et reconnaît le paramètre d’équipe.

![CloudFormation valide le template à Stockholm et reconnaît le paramètre d’équipe.](modules/01-vpc/preuves/terminal-validation.png)

**2.** La commande de déploiement est relancée. CloudFormation confirme que la stack est déjà à jour.

![La commande de déploiement est relancée. CloudFormation confirme que la stack est déjà à jour.](modules/01-vpc/preuves/terminal-deploiement.png)

**3.** La console CloudFormation affiche la stack en CREATE_COMPLETE.

![La console CloudFormation affiche la stack en CREATE_COMPLETE.](modules/01-vpc/preuves/01-stack.jpg)

**4.** La console VPC affiche le réseau de production vpc-prod-leman_bko.

![La console VPC affiche le réseau de production vpc-prod-leman_bko.](modules/01-vpc/preuves/02-vpc.jpg)

**5.** Les deux sous-réseaux sont disponibles avec leurs plages IP respectives.

![Les deux sous-réseaux sont disponibles avec leurs plages IP respectives.](modules/01-vpc/preuves/03-sous-reseaux.jpg)

**6.** La table principale contient uniquement la route locale 10.0.0.0/16.

![La table principale contient uniquement la route locale 10.0.0.0/16.](modules/01-vpc/preuves/04-route-locale.jpg)

## Module 1 — TP 2 · Instances et connectivité

[Template CloudFormation](cloudformation/01-tp2-instances.json). Les instances utilisent les adresses privées `10.0.1.10` et `10.0.2.10`. Le script de démarrage exécute les pings sur les instances et les sorties sont lues depuis la console série EC2.

**1.** Validation du template et mise à jour de la stack pour ajouter les deux instances.

![Validation du template et mise à jour de la stack pour ajouter les deux instances.](modules/01-vpc/tp2/01-cloudformation.png)

**2.** La console EC2 montre web-01_bko et app-01_bko en cours d’exécution dans eu-north-1a.

![La console EC2 montre web-01_bko et app-01_bko en cours d’exécution dans eu-north-1a.](modules/01-vpc/tp2/02-instances.jpg)

**3.** Depuis web-01_bko, le ping vers 10.0.2.10 reçoit quatre réponses sur quatre.

![Depuis web-01_bko, le ping vers 10.0.2.10 reçoit quatre réponses sur quatre.](modules/01-vpc/tp2/03-ping-web.png)

**4.** Depuis app-01_bko, le ping vers 8.8.8.8 ne reçoit aucune réponse avant l’ajout du routage Internet.

![Depuis app-01_bko, le ping vers 8.8.8.8 ne reçoit aucune réponse avant l’ajout du routage Internet.](modules/01-vpc/tp2/03-ping-app.png)

## Module 1 — TP 3 · Plan d’adressage et chevauchement

Le [template de test](cloudformation/01-tp3-chevauchement.json) tente de créer le bloc `10.0.1.128/25` dans le VPC de production depuis une stack dédiée. AWS renvoie `CREATE_FAILED` avec le motif « conflicts with another subnet ». Le bloc testé est inclus dans `10.0.1.0/24`.

| Périmètre | Bloc IPv4 | Zone | Affectation |
|---|---|---|---|
| `vpc-prod-leman_bko` | `10.0.0.0/16` | Stockholm | Production |
| `sub-public-1a_bko` | `10.0.1.0/24` | `eu-north-1a` | `web-01_bko` à `10.0.1.10` |
| `sub-prive-1a_bko` | `10.0.2.0/24` | `eu-north-1a` | `app-01_bko` à `10.0.2.10` |
| Sous-réseau données | `10.0.3.0/24` | `eu-north-1a` prévue | Réservé dans le plan |
| VPC développement | `10.1.0.0/16` | Stockholm | Réservé pour le module 5 |

Le sous-réseau privé offre **251 adresses attribuables**. Un `/24` contient 256 adresses, dont 5 sont réservées par AWS. La plage attribuable va de `10.0.2.4` à `10.0.2.254`. L’adresse de broadcast théorique est `10.0.2.255`, réservée par AWS. Le `/24` laisse de la place pour ajouter des instances et le plan garde des blocs distincts pour les autres usages du lab. Le plan est prêt pour la validation de l’Architecte réseau.

**1.** Le terminal montre la tentative de déploiement et le motif du refus remonté par CloudFormation.

![Test de chevauchement dans le terminal](modules/01-vpc/tp3/01-refus-cloudformation.png)

**2.** L’onglet Events de CloudFormation affiche le refus de créer `SubnetChevauchant`.

![Événement CREATE_FAILED dans la console AWS](modules/01-vpc/tp3/02-evenement-aws.jpg)

**3.** Le terminal confirme que le VPC contient les deux sous-réseaux prévus.

![Vérification des sous-réseaux](modules/01-vpc/tp3/03-sous-reseaux-conserves.png)

## Étapes suivantes

| Étape | Changement à versionner | Preuve |
|---|---|---|
| Module 2 | Passerelle Internet, NAT et tables de routage | Routes et tests de sortie avant retrait, pendant retrait et après rétablissement |
| Module 3 | Groupes de sécurité et NACL | Tests HTTPS et 8080, tests de blocage et règles rétablies |
| Module 4 | Network Firewall, routes symétriques et CloudWatch Logs | Pare-feu prêt, trafic autorisé et bloqué, journaux et nettoyage |

Les captures documentent les états déployés et les tests. Les modifications temporaires des routes et des règles passent aussi par CloudFormation.
