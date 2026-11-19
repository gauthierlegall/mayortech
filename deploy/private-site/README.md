# Espace privé MayorTech — préparation et mise en service bornées

Cette installation distincte utilise les comptes réels de Keycloak et une **organisation test avec uniquement des dossiers fictifs**. Elle ne constitue pas une installation de la mairie. Aucun accès messagerie ni moteur IA distant n'est activé. L'application publique et l'identité de Registrar restent séparées.

Le candidat utilise les images déjà présentes, sans téléchargement : Keycloak 26.8.2, PostgreSQL 17, Nginx et l'image Travaux revue. Les empreintes sont épinglées dans `compose.yaml`. L'identité est `https://identite.kerforge.com/realms/mayortech` ; l'application est `https://espace.kerforge.com`.

## Opérations

Depuis la racine du dépôt :

```powershell
python deploy/private-site/operator.py plan
python deploy/private-site/operator.py preflight
# Seulement après revue indépendante du candidat exact :
python deploy/private-site/operator.py apply --reviewed
python deploy/private-site/operator.py status
python deploy/private-site/operator.py backup
```

`plan` reste local. Les autres commandes réutilisent le transport SSH opérateur existant. Aucune valeur de credential, environnement résolu, réponse OAuth, lien de validation ou journal brut n'est retournée. Les résultats sont des booléens, URLs publiques, empreintes et chemins opérateur. Un échec renvoie un code générique.

L'opérateur exige le marqueur exact `/opt/apps/mayortech-private/.mayortech-private-owner`, les propriétaires attendus et les répertoires privés 0700. Les fichiers secrets sont créés exclusivement en 0600, sans remplacement. La clé SMTP Resend dédiée, limitée au domaine kerforge.com, existe déjà côté serveur ; elle n'est jamais copiée sur le poste. Les autres secrets sont générés sur le serveur. Le realm importé est lisible seulement par l'UID Keycloak ; le coffre seulement par l'UID applicatif. Les fichiers publics montés sont 0644.

Les seuils de lancement sont strictement plus de 3 Gio libres sur disque et de 2,5 Gio de mémoire disponible. Les ressources Docker doivent être absentes ou porter les labels de cette application. Aucun volume voisin n'est adopté. Un candidat modifié face à une installation existante est refusé avant toute suspension. Le premier lancement écrit uniquement son fichier Caddy, conserve l'empreinte des configurations voisines et valide avant rechargement. En cas d'échec, il retire seulement sa route créée et arrête seulement ses services ; il conserve les volumes et données pour diagnostic. Il n'exécute ni prune, ni down, ni suppression récursive.

## Identité et protections

Les formulaires de connexion, inscription, vérification d'adresse et TOTP proviennent de Keycloak. Notre thème contient des styles, une police sous OFL et le logo ; aucun formulaire de mot de passe maison. Le client est confidentiel, Authorization Code + PKCE S256, avec une URI de retour exacte. Le backend exige `email_verified` et les méthodes réellement exécutées `pwd` et `otp`. Le realm ne forge pas ces assertions. Une première inscription peut nécessiter ensuite une connexion normale pour obtenir les deux références ; ce cas doit être vérifié en recette réelle.

SMTP utilise le port 2465 en TLS implicite, certificat et nom d'hôte vérifiés, sans option ANY, debug ou trust-all. Les comptes ne reçoivent aucun rôle administrateur applicatif automatiquement. Le service d'administration de bootstrap reste côté serveur et aucune route `/admin`, `/realms/master` ou autre realm n'est publiée. Les tests QA devront créer puis supprimer uniquement un compte synthétique explicitement identifié.

Caddy remplace les en-têtes IP fournis par le client. Il utilise `CF-Connecting-IP` seulement si le pair TCP appartient aux plages officielles Cloudflare ; sinon l'adresse du pair. Nginx ne fait confiance qu'à l'adresse exacte inspectée de Caddy. L'application ne fait confiance qu'à cette même adresse. Keycloak est sur son réseau privé derrière Nginx, sans connexion à `caddy_net` ni port hôte. Les limites Nginx protègent aussi les actions natives d'inscription et de renvoi de mail, avec budgets IP et global et réponse 429. Les accès ne sont pas journalisés ; les erreurs des deux sites sont traitées par une réponse générique sans reflet d'URL. Le niveau DEBUG du Caddy partagé doit rester désactivé.

## Sauvegardes et limites

Le checkpoint initial et la commande `backup` produisent un export PostgreSQL custom validé par `pg_restore --list` et une sauvegarde SQLite via l'API native avec vérification d'intégrité. Les fichiers sont 0600 dans un dossier 0700 du seul espace dédié. **Ils sont locaux, non chiffrés et non hors site** : le DTO l'indique explicitement. Ce contrôle n'est pas un test de restauration complet ni un PRA. Il reste à mettre en place un dépôt chiffré indépendant et à réaliser une restauration isolée avant de considérer l'exploitation durable prête.

Les tests purs de l'opérateur et la recette isolée de la garde Nginx sont distincts du démarrage réel et du parcours navigateur. La présence de DNS, SMTP ou d'un realm importé ne prouve pas la réception du mail, l'inscription, le TOTP ni l'ouverture de session. Ces résultats doivent être consignés séparément après la recette réelle. Aucune qualification RGPD, ANSSI ou certification n'est revendiquée.

Les probes des APIs applicatives passent par le loopback du conteneur avec Host et Origin explicites. L'attente du certificat et la découverte d'identité utilisent le vrai `OIDCService.metadata()` : client HTTPX, règles réseau et vérification TLS de l'application, sans remplacement de User-Agent. Le parcours HTTPS public de l'interface doit ensuite être vérifié dans un vrai navigateur ; le reçu opérateur le marque en attente. Une politique Cloudflare qui refuse Python urllib ne peut donc pas être confondue avec un échec du client OIDC ni être contournée en maquillant ce client.

Sources primaires : [Keycloak Server](https://www.keycloak.org/server/containers), [themes](https://www.keycloak.org/ui-customization/themes), [TLS SMTP Keycloak 26.8.2](https://github.com/keycloak/keycloak/blob/26.8.2/services/src/main/java/org/keycloak/email/DefaultEmailSenderProvider.java), [gestion des erreurs Caddy 2.10.2](https://github.com/caddyserver/caddy/blob/v2.10.2/modules/caddyhttp/server.go), [plages IPv4 Cloudflare](https://www.cloudflare.com/ips-v4), [IPv6](https://www.cloudflare.com/ips-v6).

## Correction du contrat de claims Keycloak 26

Le premier candidat excluait le scope natif `basic` en définissant explicitement `profile,email`. Les JWT signés réels ne contenaient donc pas `auth_time` et le backend les refusait correctement, y compris après une authentification avec mot de passe et OTP. Le template inclut désormais `basic`. Ce scope porte le mapper natif de la date d'authentification ; aucun claim constant n'est ajouté et les contrôles signature, nonce, date et MFA restent obligatoires. [Source Keycloak 26.8.2](https://github.com/keycloak/keycloak/blob/26.8.2/services/src/main/java/org/keycloak/protocol/oidc/OIDCLoginProtocolFactory.java).

Pour l'installation existante, `basic_scope.py plan` lit uniquement le client exact `mayortech-space` du realm `mayortech`, retrouve les UID natifs et vérifie le mapper `AUTH_TIME` vers `auth_time`. Après revue du plan, `basic_scope.py apply --reviewed-fingerprint <empreinte>` ajoute exclusivement ce lien natif, sauvegarde l'ensemble initial en 0600 et vérifie que les autres liens sont conservés. En cas d'échec de cette vérification, il retire seulement le lien qu'il vient d'ajouter. Il ne modifie pas le realm, les mappers, le secret client ou un autre client. Ne pas relancer l'installation complète pour cette migration : son reçu FF90 reste une preuve historique distincte.

L'enrôlement initial et la connexion avec le facteur sont deux événements différents : la comparaison signée a montré `amr=[pwd]` après configuration TOTP, puis `amr=[pwd,otp]` à la reconnexion normale. L'interface doit demander cette reconnexion explicitement et le backend doit continuer à refuser une session tant que les deux références authentifiées ne sont pas présentes. Les preuves avant/après du contrat et le test du parcours utilisateur restent séparés.
