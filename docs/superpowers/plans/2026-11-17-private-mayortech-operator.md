# Préparer le compte MayorTech et l’espace privé de présentation

Steering racine : réutiliser Keycloak26.8.2 existant sur `https://registrar-ia.com/native-identity`, ajouter seulement un realm `mayortech` et un espace Travaux staging séparé sur `espace.kerforge.com`. Aucune nouvelle instance IdP/PostgreSQL et aucun changement des autres realms ou du hostname global.

## Contraintes observées

- VPS : 1,24Gio libres, charge1min19,81 pour4CPU ; aucune activation supplémentaire à ce niveau de capacité. Aucun nettoyage de volume/service voisin.
- Le Keycloak existant sert actuellement des comptes de services ; aucun accès admin opérateur trouvé, aucun profil kcadm. `.native-bootstrap.json` est un manifeste, pas un secret d’administration. Ne pas détourner les credentials du client de services.
- Réseau partagé `caddy_net`, alias IdP `registrar-native-keycloak:8080`, chemin fixe `/native-identity`. L’issuer du nouveau realm doit rester exact.
- Secrets générés/provisionnés côté serveur dans un coffre séparé0600 ; aucune clé Mistral Registrar copiée. SMTP Resend avec clé dédiée limitée à l’expéditeur approuvé, fournie séparément par l’agent infra.

## Livrables de préparation

- [ ] Realm natif pour comptes personnels : adresse vérifiée, TOTP requis, vrai AMR pwd/otp, client code+PKCE confidentiel, redirect exact, aucun utilisateur importé ni auto-admin.
- [ ] Compose Travaux privé distinct, image déjà revue réutilisée sans pull, base et tenant test marqués séparés, IA démo et connecteurs métier bloqués côté serveur.
- [ ] Fragments Caddy limités au nouveau domaine applicatif et au nouveau realm ; aucune route admin/master exposée ni remplacement des routes existantes.
- [ ] Notice opérateur avec génération serveur des secrets, sauvegardes et restauration de contrôle, validation capacité/issuer/TLS/MFA, et absence de déploiement de ce candidat.
- [ ] Vérification locale des fichiers candidats, sans credential ni requête de provisioning.
