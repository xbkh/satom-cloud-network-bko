# ADR 001 · Région, dépôt et environnements

**Décision.** Exécuter les validations à Stockholm (`eu-north-1`), selon la décision de l’utilisateur, dans le dépôt GitHub déjà utilisé pour les modules. Le dépôt désigné par l’énoncé n’était pas accessible avec le compte courant.

L’environnement GitHub `dev` est limité à `main` et à la branche de préparation. L’identité OIDC est liée au dépôt et à cet environnement. L’environnement `prod` exige une approbation humaine. La démonstration publique existante a sa propre stack. Une promotion de test vise une stack nommée séparément.

**Conséquence.** Une revue indépendante et la validation de l’organisation de rendu sont nécessaires pour déclarer une promotion conforme au TP.
