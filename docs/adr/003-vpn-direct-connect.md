# ADR 003 · Interconnexion des sites et preuve de bascule

Les adresses de routeurs du cahier des charges sont des adresses de documentation. AWS a créé les VPN et les routes, avec des tunnels `DOWN`. Le passage de GRE vers IPsec et le retour ont été vérifiés dans la maquette BGP. La passerelle Direct Connect est associée à la Transit Gateway. Une liaison physique et des routeurs publics réels relèvent d’une validation distincte.

Les résultats de simulation, les adresses, les routes et les captures sont documentés dans les sections des [modules 7 et 8](../../README.md#module-7--vpn-site-to-site). Aucun débit physique ni taux de disponibilité n’est déduit de la maquette.
