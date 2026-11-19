# Formulaires officiels Keycloak avec présentation MayorTech

Le thème `mayortech` étend le thème de connexion officiel **`keycloak.v2` de Keycloak26.8.2**. Il personnalise uniquement la présentation : fond clair, accent bleu, DM Sans auto-hébergée et marque illustrative MayorTech. Login, inscription, réinitialisation du mot de passe, TOTP et passkeys restent les formulaires et contrôleurs natifs de Keycloak ; aucun template FTL ou script d’authentification n’est remplacé.

Le thème comprend les fichiers DM Sans déjà utilisés par le projet et leur licence SIL OFL1.1. Voir `mayortech/FONT_LICENSE.md` et `mayortech/ASSETS.md` pour la provenance. Aucune police, feuille de style ou image n’est chargée depuis un tiers.

## État au 18 novembre 2026

Une instance native distincte est installée à `https://identite.kerforge.com/realms/mayortech`, pour l’application `https://espace.kerforge.com`. Elle porte les comptes personnels et le second facteur d’une organisation test fictive. Le portail public et les [pages légales](https://travaux.kerforge.com/mentions-legales.html) sont publiés séparément. La recette HTTPS réelle a réussi **20 contrôles avec 8 captures Full HD/mobile** : premier enrôlement sans session, vraie reconnexion mot de passe + TOTP, choix de l’organisation, accès bornés et révocation. Elle utilisait un compte synthétique `.invalid` prévalidé, supprimé et révoqué après le test. **Elle ne qualifie ni l’inscription avec vérification d’un email réel ni sa réception.**

La migration ciblée de l’action native `UPDATE_PASSWORD` est appliquée et relue indépendamment : action activée, sans action par défaut, priorité 15, autres réglages conservés. **La définition native du mot de passe puis l’accès avec ce nouveau mot de passe et TOTP sont validés : 24/24 contrôles et 10 captures**, avec le compte synthétique prévalidé ensuite supprimé et révoqué. Le blocage de cette correction est levé. Les 23 contrôles des premières pages d’inscription/récupération restent limités à leur affichage ; une inscription avec vérification d’un email réel ou une récupération par lien reçu en boîte restent non qualifiées.

La mise en page du parent Keycloak 26 peut ajouter son propre espacement au conteneur : le thème inclut le correctif borné `padding-inline:0` pour le conteneur de connexion. Le JAR installé a l’empreinte `4288841cc62f7f3ed06373c178741835e08b13a2c4fa5106e1a092861fa13afd`, consignée dans le reçu serveur `theme-updates/20261118T112341Z-01bb3471/receipt.json`. Le code de l’opérateur de cette maintenance porte l’empreinte `17b54dd155cb3013de4439b343302d70d5a3630b76502ffb4d995032cc8e9da5` ; cette empreinte n’est pas celle du CSS. Voir [l’opérateur privé et ses limites](../../private-site/README.md). Aucun contrôleur natif ni politique d’authentification n’est remplacé par cette correction visuelle.

Le nom de ressource **`mayortech-20261118-1.css`** est installé et vérifié après maintenance, sans changement du realm. Les réponses d’origine en identity et gzip décompressé puis le CSS reçu à travers le CDN ont la même empreinte `f02631604b720096f19f215156d222944480f8b82f2fb19eb71232062d5f85d8` (3 284 octets). Dans un Chrome neuf, la carte mesure **490 px en Full HD** avec `padding-inline:0`, puis **362 px sur un écran de 390 px**, sans débordement horizontal. L’ancien `mayortech.css` n’est plus référencé. Les captures ont été inspectées avec des formulaires vides, sans identifiant saisi ; ces contrôles visuels n’envoient aucun message. Preuves : `test-results/native-css-diagnostic-20261118/versioned-origin-encoding.json` et `post-versioned/edge-measurements.json` sous ce même dossier.

## Préparer l’archive

Depuis la racine du projet :

```powershell
.\.venv\Scripts\python.exe scripts/package_keycloak_theme.py --output dist/mayortech-keycloak-theme-2026-11-18-filename-v1.jar
```

Le packager crée un JAR standard avec `META-INF/keycloak-themes.json`. Il lit seulement la liste fermée des fichiers du thème, refuse les liens/jonctions et ne remplace jamais un fichier existant. Il n’exige pas de JDK, n’installe aucun paquet et ne démarre aucun serveur.

Les archives du 17 novembre (`fd30180d…18eadd`) et du 18 novembre sans suffixe (`5c884638…b7069`) sont des références immuables : ne pas les supprimer ni les reconstruire depuis la source courante. Le JAR `filename-v1` installé porte l’empreinte `4288841cc62f7f3ed06373c178741835e08b13a2c4fa5106e1a092861fa13afd`. S’il existe déjà, vérifier et réutiliser cet artefact ; une reconstruction exige une destination distincte, puis une nouvelle revue de son empreinte.

Le CSS est publié sous le nom `mayortech-20261118-1.css`, avec exactement les mêmes octets que le correctif CSS du 18 novembre. Seuls son nom de ressource et la ligne `styles` changent dans ce nouveau JAR. Le nom distinct évite à la fois le cache du navigateur, le CDN et le cache gzip persistant de Keycloak : la sonde du 18 novembre a montré que ce dernier servait encore les anciens octets gzip même avec un paramètre de version dans l’URL. Le modèle officiel concatène le chemin du thème et chaque ressource sans remplacer nos formulaires. [Modèle Keycloak26.8.2](https://github.com/keycloak/keycloak/blob/26.8.2/themes/src/main/resources/theme/keycloak.v2/login/template.ftl), [cache des thèmes](https://www.keycloak.org/ui-customization/themes).

Pour la maintenance existante, préparer un nouveau plan :

```powershell
.\.venv\Scripts\python.exe deploy/private-site/theme_update.py plan --jar dist/mayortech-keycloak-theme-2026-11-18-filename-v1.jar --review-id theme-filename-cache-20261118
```

L’application du plan exige `apply`, les mêmes arguments, `--reviewed`, `--expected-theme-sha256` et `--expected-status-sha256` avec les deux valeurs renvoyées par ce plan frais. L’opérateur accepte uniquement les trois empreintes revues (17 novembre, correctif CSS18, cible versionnée), sauvegarde le JAR effectivement installé, puis recrée Keycloak et sa garde Nginx. Il conserve l’application, les fichiers du realm, SMTP, les secrets et les politiques d’authentification. La recette après maintenance doit vérifier le corps CSS décompressé en gzip et en identity, puis mesurer une carte de490px en Full HD et l’absence de débordement mobile dans un navigateur neuf. La présence du nouvel URL ou un HTTP200 seul ne suffit pas.

Pour une nouvelle instance, l’exploitant installe l’archive validée dans `providers/` puis suit sa procédure de construction/redémarrage. Sélectionner `mayortech` comme Login Theme du realm, ou définir `"loginTheme":"mayortech"` dans une préparation de realm. Sur l’installation existante, utiliser la maintenance ciblée et son reçu ; ne pas relancer le bootstrap ni modifier les thèmes livrés à l’intérieur de Keycloak. La préparation de cette notice ne reconstruit pas le JAR et ne redémarre aucun service. [Guide officiel des thèmes et du packaging](https://www.keycloak.org/ui-customization/themes), [propriétés du parent examiné](https://github.com/keycloak/keycloak/blob/26.8.2/themes/src/main/resources/theme/keycloak.v2/login/theme.properties).

## Connexion, inscription et récupération

Le portail Travaux collecte seulement un email facultatif pour préremplir les formulaires natifs, via `login_hint`. Le champ est borné à254 caractères, refuse les contrôles et les entrées mal formées avant toute requête IdP. Il n’est pas une preuve d’identité et n’est pas stocké dans la table des flux OIDC. Le mot de passe et le code TOTP ne passent pas dans les formulaires Travaux.

`POST /api/v1/auth/start` accepte un corps strict :

```json
{"intent":"login","login_hint":"personne@example.invalid"}
```

Les intents possibles sont `login`, `signup` et `recovery`. `TRAVAUX_OIDC_RESET_URL` active explicitement le point d’entrée de récupération. Pour Keycloak, utiliser l’URL HTTPS de cette instance finissant par `/realms/<realm>/protocol/openid-connect/forgot-credentials`, dans la liste d’hôtes autorisés. Ne pas rediriger directement vers les endpoints internes `/login-actions/`. La configuration est incluse dans le fingerprint : changer l’URL invalide les flux de connexion précédemment ouverts. [Point d’entrée officiel de récupération](https://www.keycloak.org/docs/latest/server_admin/index.html#redirect-to-registration-or-reset-credentials-screen).

Le retour est fixé côté serveur à `/connexion.html?auth=connected`, `pending` ou `failed`. Aucun paramètre utilisateur ne choisit la destination. Tous les intents conservent PKCE-S256, nonce, état chiffré et à usage unique, vérification de signature/issuer/audience et politique MFA. Une récupération de mot de passe qui ne produit pas les claims MFA attendus ne donne aucune session Travaux.

Le premier retour après configuration de TOTP peut porter uniquement `amr=[pwd]`. Le code publié distingue ce retour signé et valide d’un échec d’identité et demande une reconnexion explicite ; il ne crée alors aucune session applicative. La reconnexion doit réellement porter `pwd` et `otp`. Le marqueur `auth=reauthenticate` n’est qu’une instruction d’interface : il n’accorde aucun droit. Le scope Keycloak natif `basic` est nécessaire à `auth_time` ; la correction conserve ce mapper natif, sans valeur statique. Voir [le contrat et la migration bornée](../../private-site/README.md#correction-du-contrat-de-claims-keycloak-26).

`recovery_available` signifie seulement que ce point d’entrée est configuré ; cela ne prouve pas la disponibilité d’un serveur mail. Si l’URL n’est pas configurée, l’API refuse explicitement cet intent et le portail doit expliquer cette indisponibilité.

Dans Keycloak 26.8.2, la vérification d’email active reporte nativement la définition du mot de passe à l’action `UPDATE_PASSWORD`, après validation de l’adresse. L’absence de champ de mot de passe sur la première page d’inscription est donc attendue ; l’option pour l’imposer avant la vérification est dépréciée. Le parcours prévu ici est **nom/email → vérification de l’email → mot de passe → TOTP → reconnexion → organisation**. Les vérifications des formulaires sans soumission ne qualifient pas ce parcours d’inscription avec réception d’email. [Source officielle au tag utilisé](https://raw.githubusercontent.com/keycloak/keycloak/26.8.2/services/src/main/java/org/keycloak/authentication/forms/RegistrationPassword.java).

L’enregistrement appliqué est `UPDATE_PASSWORD`, `enabled=true`, `defaultAction=false`, priorité 15, avec sauvegarde, contrôle de concurrence et revue indépendante. Le helper revu porte l’empreinte `e19b96ec5bbae14ccaebf750806f6a8240cf902b214db64b286fd8ca507ff35e` ; sa revue comporte 22 tests de migration et 2 tests de préparation du compte de recette. Le readback `test-results/private-native-entry-final/post-required-action.json` confirme qu’aucun changement n’est encore requis et `post-password-action-preservation.json` conserve 19/19 contrôles. Le test réel `test-results/private-password-update-live/checks.json` a défini le nouveau mot de passe dans le formulaire natif, puis exercé TOTP, reconnexion MFA vers l’organisation, refus d’un mauvais OTP et révocation après suppression. Vérification d’adresse et exigences MFA restent actives ; aucun message n’a été envoyé par ces contrôles.

## SMTP configuré, réception à prouver

Le relais Resend de la région européenne est configuré dans l’IdP pour le domaine `kerforge.com`, sur le port **2465**, en TLS implicite avec vérification du certificat et du nom d’hôte. La clé dédiée reste sur le serveur, hors source et captures. La sonde a validé TLS, l’authentification SMTP et l’acceptation de l’expéditeur, puis annulé la transaction avec RSET/QUIT sans destinataire ni DATA ; elle n’a envoyé aucun message. **La réception d’un email de vérification ou de récupération n’est pas encore attestée dans le manifeste préparatoire du 18 novembre.** Un relais configuré ne suffit pas à prouver l’émission ou la réception. Ne pas annoncer « email reçu » sans observation et ne pas désactiver la vérification d’adresse ou le second facteur pour simuler un parcours réussi. [Prérequis mail de la récupération native](https://www.keycloak.org/docs/latest/server_admin/index.html#_forgot_password).

La sortie réseau depuis le namespace de Keycloak a également réussi TLS, EHLO et QUIT, sans AUTH, lecture de credential ou émission de message ; le conteneur éphémère de sonde a été supprimé. Cette preuve (`test-results/private-native-entry-final/smtp-keycloak-namespace.json`) complète le test d’authentification SMTP côté hôte, sans démontrer la réception d’un email.

Les tests du contrôleur utilisent de vrais ID tokens signés de recette et un transport IdP contrôlé ; ils restent distincts de la recette distante. Le JAR produit a été relu par un consommateur ZIP standard et ses limites de fichiers/collision contrôlées. La comparaison distante des claims puis la recette HTTPS réelle ont confirmé le rôle de `basic/auth_time` et la différence entre enrôlement et reconnexion, avec la limite du compte prévalidé décrite plus haut. Voir `test-results/private-identity-live/checks.json`. Le précédent laboratoire local avait rencontré l’interception TLS Avast, sans contournement : voir `docs/RECETTE_KEYCLOAK_LOCALE_2026-11-17.md`. L’état courant et les points restant à prouver sont dans [le manifeste du 18 novembre](../../../docs/verification-production-2026-11-18.json).
