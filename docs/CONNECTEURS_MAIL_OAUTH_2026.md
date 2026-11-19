# Raccordement Microsoft 365 et Gmail

Le code fournit un parcours OAuth côté serveur, puis une lecture des messages Graph/Gmail dans les dossiers sélectionnés. Il est distinct de la connexion des utilisateurs à Travaux. Les permissions de calendrier ne sont pas demandées par ces connecteurs mail ; EWS et CalDAV restent disponibles séparément.

Les transports ont été vérifiés par des contrats HTTP locaux déterministes, avec des identités et messages fictifs. Aucun compte réel, application Entra/Google ou consentement municipal n’a été créé par ce développement. La validation avec la DSI et une boîte de recette reste nécessaire avant activation.

## Paramètres serveur

Le mode doit être protégé (`pilot`/`staging`), avec une origine publique HTTPS exacte. Les modes de démonstration refusent le raccordement. Les variables ci-dessous contiennent uniquement des noms et exemples réservés ; les vraies valeurs restent dans le gestionnaire de secrets serveur.

| Fournisseur | Variables requises |
| --- | --- |
| Google | `TRAVAUX_GOOGLE_OAUTH_CLIENT_ID`, `TRAVAUX_GOOGLE_OAUTH_CLIENT_SECRET`, `TRAVAUX_GOOGLE_OAUTH_ALLOWED_DOMAINS` |
| Microsoft 365 | `TRAVAUX_MICROSOFT_OAUTH_CLIENT_ID`, `TRAVAUX_MICROSOFT_OAUTH_CLIENT_SECRET`, `TRAVAUX_MICROSOFT_OAUTH_TENANT_ID`, `TRAVAUX_MICROSOFT_OAUTH_ALLOWED_DOMAINS` |

Les domaines de boîte sont une liste séparée par des virgules, par exemple `commune.example,prestataire.commune.example`. Aucun joker ni suffixe implicite : un sous-domaine doit être déclaré séparément. L’adresse réelle de la boîte est contrôlée après l’autorisation, sur la réponse de l’API du fournisseur ; le paramètre Google `hd` ne sert que d’indication d’affichage.

Les sorties sont soumises à `TRAVAUX_CONNECTOR_EGRESS_APPROVED=true`, aux hôtes explicitement autorisés et au coffre existant. Pour les deux fournisseurs, les hôtes requis sont :

```text
accounts.google.com
oauth2.googleapis.com
gmail.googleapis.com
login.microsoftonline.com
graph.microsoft.com
```

Déclarer seulement les hôtes des fournisseurs effectivement activés dans `TRAVAUX_CONNECTOR_ALLOWED_HOSTS`, en conservant les hôtes EWS/CalDAV déjà autorisés le cas échéant. Les requêtes externes refusent les redirections et les proxys hérités de l’environnement ; TLS doit être vérifié. Les journaux TLS de débogage (`SSLKEYLOGFILE`, `QUICLOGDIR`) bloquent les appels.

## Enregistrement Microsoft

Créer une application **web confidentielle dans le tenant Entra de la collectivité**, avec son identifiant de tenant GUID explicite. La configuration n’utilise ni `common`, ni les permissions Graph d’application sur toutes les boîtes. Déclarer exactement :

```text
https://votre-domaine-institutionnel.example/api/v1/integrations/oauth/microsoft365/callback
```

Permissions déléguées demandées : `User.Read`, `Mail.Read`, `offline_access`. Les règles du tenant peuvent demander l’intervention de son administrateur. Le code ne demande ni `Mail.ReadWrite` ni `Mail.Send`. Il lit le profil et utilise Graph pour parcourir les dossiers, suivre leur delta et obtenir le MIME. [Flux officiel](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow), [permissions Graph](https://learn.microsoft.com/en-us/graph/permissions-reference), [dossiers](https://learn.microsoft.com/en-us/graph/api/user-list-mailfolders?view=graph-rest-1.0), [delta](https://learn.microsoft.com/en-us/graph/api/message-delta?view=graph-rest-1.0), [MIME](https://learn.microsoft.com/en-us/graph/api/message-get).

La déconnexion supprime les jetons locaux et désactive la lecture. Elle ne prétend pas retirer tout le consentement Entra : cette opération doit être réalisée dans l’administration du tenant lorsque nécessaire. Le connecteur n’obtient pas de permission d’écriture d’annuaire pour automatiser ce retrait.

## Enregistrement Google

Activer Gmail API, créer une application OAuth **web** et définir son écran de consentement. Déclarer exactement :

```text
https://votre-domaine-institutionnel.example/api/v1/integrations/oauth/google/callback
```

Le seul scope demandé est `https://www.googleapis.com/auth/gmail.readonly`. Il est classé **restreint** par Google. Les exigences de vérification et d’évaluation de sécurité dépendent du mode de diffusion et des exceptions applicables, notamment l’usage interne d’une organisation. Un réglage de notre application ne remplace pas cette qualification. [Scopes Gmail](https://developers.google.com/workspace/gmail/api/auth/scopes), [vérification des scopes restreints](https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification), [consentement côté serveur](https://developers.google.com/identity/protocols/oauth2/web-server).

Le parcours demande un consentement explicite et un accès hors présence de l’utilisateur. Google peut ne pas retourner de jeton de renouvellement dans certaines situations ; le code refuse alors de présenter une connexion durable comme terminée. Il faut vérifier l’application et le consentement avec l’administrateur, puis recommencer. Une déconnexion locale est toujours conservée même si la révocation Google distante ne peut pas être confirmée.

## Parcours et garanties du code

1. Un administrateur connecté démarre une demande par POST protégé contre le CSRF. Le serveur crée un état aléatoire, son empreinte, un PKCE S256 et une liaison navigateur distincte. L’état expire après **600 secondes**, ne peut servir qu’une fois et est associé à l’acteur, au tenant, au fournisseur et à la session de départ.
2. Le navigateur ouvre la page officielle du fournisseur. Aucun mot de passe Microsoft/Google n’est saisi dans Travaux.
3. Le retour OAuth utilise un cookie de liaison `Secure`, `HttpOnly`, `SameSite=Lax`, limité au chemin OAuth. Il ne dépend pas du cookie principal `SameSite=Strict`, absent lors d’une navigation externe. Le serveur vérifie à nouveau la session de départ et les habilitations, y compris après la lecture du profil. Un logout ou un retrait de droits bloque la création.
4. Le code et le PKCE sont échangés côté serveur. Les jetons sont chiffrés par le coffre lié au tenant ; ils ne figurent pas dans les DTO ou les destinations de redirection. Aucun jeton ID décodé sans vérification n’est utilisé pour authentifier un utilisateur de Travaux.
5. Le retour ouvre le compte autorisé dans **Connexions → Messagerie**. Le bouton de choix des dossiers vérifie la boîte et affiche ses dossiers ou libellés. L’administrateur enregistre ceux qu’il souhaite importer, puis lance la première lecture. Le choix des dossiers limite l’import et le partage dans MayorTech ; les permissions du fournisseur déterminent les droits réels du jeton.
6. Le renouvellement utilise une lease SQLite et une comparaison du ciphertext précédent. Deux processus ne doivent pas faire tourner le même refresh token simultanément ; une déconnexion concurrente ne peut pas être écrasée par une réponse tardive. Les créations, renouvellements, déconnexions et reprises explicites rejoignent le journal organisationnel sans secret ou corps de mail.

Les callbacks contiennent un code éphémère dans leur URL initiale. Les journaux du proxy, de la supervision et des outils d’analyse doivent exclure ou masquer la query de ces deux routes. L’application retourne `Referrer-Policy: no-referrer`, `Cache-Control: no-store` et redirige vers `/espace.html#/connexions`. En cas de succès, elle transmet uniquement le résultat et l’identifiant interne du compte créé. L’interface recoupe cet identifiant avec les connexions autorisées renvoyées par le serveur. L’accès Uvicorn est désactivé dans le déploiement existant ; vérifier aussi la configuration effective du proxy.

## Lecture durable et reprise

Les API de boîte ne sont appelées qu’en **GET**. Graph utilise un delta propre à chaque dossier, Gmail un inventaire initial des messages puis l’historique. Les requêtes de pagination sont bornées, restent sur l’API du fournisseur et dans le dossier choisi. Le lecteur traite au plus cinq pages de cinq changements par passage, avec un ordre évitant d’affamer les autres dossiers.

Le MIME et ses pièces utilisent le circuit d’import existant, avec originaux, empreintes, sources et tâches d’extraction. Le checkpoint chiffré est validé dans la même transaction que les imports du lot. Une erreur de persistance laisse le checkpoint inchangé. Un retrait distant produit un événement à examiner et n’efface aucune preuve locale. [Synchronisation Gmail](https://developers.google.com/workspace/gmail/api/guides/sync), [historique](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.history/list), [message RAW](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/get).

Un curseur périmé retourne `mail_cursor_expired`. La reprise intégrale est une action explicite : POST `/api/v1/integrations/connections/{id}/reset-mail-sync`, avec `{expected_revision, confirm:true}`. Les originaux et dossiers locaux sont conservés ; les doublons MIME de la même connexion sont reconnus. Les reprises historiques par plage de dates existantes restent **EWS seulement** ; l’inventaire initial cloud n’est pas présenté comme cette fonction de backfill daté.

Les limites actuelles sont explicites : 100 dossiers/labels vérifiés par connexion, arborescence Graph de huit niveaux, MIME de 10 Mo, réponses JSON bornées et lecture à la demande depuis le parcours existant. Aucun webhook Google Pub/Sub ou abonnement Graph, aucune synchronisation de calendriers cloud ni envoi de message n’est annoncé comme livré par ce lot.

## Recette avant activation

- Vérifier une boîte de recette du domaine autorisé et une boîte extérieure refusée ; tester consentement refusé, session expirée et droits retirés.
- Tester dossier imbriqué, pièce jointe, pagination, modification et retrait distants, reprise après échec et curseur périmé.
- Tester rotation du secret d’application, du coffre, du refresh token et révocation ; vérifier les journaux réels du proxy.
- Confirmer les destinataires de l’espace et les règles de conservation avant de lire un dossier municipal réel.

Commandes locales : `python -m pytest tests/test_mail_oauth.py tests/test_cloud_mail.py tests/test_connection_hub.py tests/test_calendars.py tests/test_mail_backfill.py -q`, puis compilation et Ruff sur les nouveaux modules. Les résultats locaux ne constituent pas un agrément RGPD, une certification de cybersécurité ou une recette des services fournisseurs réels.
