# Préparer l’inscription et la double authentification

L’exemple cible **Keycloak 26.8.2**, release officielle du 5 novembre 2026. Cette préparation ne déploie aucun service et ne fournit aucun compte ou secret réel. Une copie a depuis été importée avec succès dans un processus Keycloak local jetable ; le parcours d’inscription/MFA reste à qualifier, car la protection TLS du poste refuse la CA fictive. Voir le [compte rendu de recette](../../docs/RECETTE_KEYCLOAK_LOCALE_2026-11-17.md). [Release](https://github.com/keycloak/keycloak/releases/tag/26.8.2), [guide officiel](https://www.keycloak.org/docs/latest/server_admin/index.html).

`realm-test.example.json` active l’inscription, la vérification d’adresse et l’enrôlement TOTP. Le flux navigateur exige ensuite mot de passe et OTP. Les valeurs `pwd` et `otp` du claim `amr` viennent du mapper AMR et des exécutions effectivement terminées, pas d’un mapper qui déclarerait tous les utilisateurs « MFA ». Leur durée est bornée à une heure. [Mapper au tag examiné](https://github.com/keycloak/keycloak/blob/26.8.2/services/src/main/java/org/keycloak/protocol/oidc/mappers/AmrProtocolMapper.java), [calcul des références et de leur validité](https://github.com/keycloak/keycloak/blob/26.8.2/services/src/main/java/org/keycloak/protocol/oidc/utils/AmrUtils.java), [constantes de configuration](https://github.com/keycloak/keycloak/blob/26.8.2/server-spi-private/src/main/java/org/keycloak/models/Constants.java).

Pour cet exemple, Travaux attend `TRAVAUX_OIDC_REQUIRED_AMR=pwd,otp`. Ne pas ajouter un ACR portant le nom « phishing resistant » : TOTP ne donne pas cette propriété. Pour une cible WebAuthn/passkey, définir et tester un autre flux ainsi que les claims correspondants avant de changer la politique de l’application.

## Préparation opérateur

1. Choisir deux origines HTTPS exactes : identité et application de test. Fournir `TRAVAUX_TEST_PUBLIC_ORIGIN` au conteneur pour remplacer les paramètres des URI de retour ; aucun wildcard n’est autorisé dans le client fourni.
2. Examiner les images officielles et conserver leurs digests dans `TRAVAUX_KEYCLOAK_IMAGE` et `TRAVAUX_KEYCLOAK_POSTGRES_IMAGE`. L’exemple Compose refuse de choisir une image implicitement. Séparer mots de passe et bootstrap administrateur de la source ; utiliser le gestionnaire de secrets et contrôler leur rotation.
3. Configurer le proxy HTTPS, les seules adresses proxy de confiance et les journaux. Le port HTTP de l’identité est publié seulement sur la boucle locale ; aucun `start-dev` n’est prévu.
4. Configurer un SMTP approuvé dans Keycloak. Aucun serveur SMTP ni mot de passe n’est inclus ici ; l’inscription ne peut pas finir sa vérification d’adresse tant que ce point manque.
5. Importer la préparation dans un environnement autorisé, récupérer le secret du client confidentiel `travaux-test` via l’administration et le placer uniquement dans `TRAVAUX_OIDC_CLIENT_SECRET` côté Travaux.
6. Configurer Travaux : `TRAVAUX_AUTH_MODE=oidc`, issuer exact du realm, client ID, secret, hôtes autorisés, sortie IdP approuvée et politique AMR ci-dessus. Définir `TRAVAUX_OIDC_SIGNUP_URL` sur l’URL officielle `/realms/travaux-test/protocol/openid-connect/registrations` de cette instance ; aucune inscription dynamique de client n’est utilisée.
7. Faire `docker compose ... config --quiet` dans le périmètre privé. Ne pas imprimer une configuration résolue contenant les mots de passe. Ce Compose n’a pas été lancé. Le laboratoire séparé a utilisé seulement des processus portables, adresses loopback et identités fictives, sans domaine ni service public.

## Recette indispensable

Créer un utilisateur de recette par l’IdP, vérifier son email, configurer TOTP, puis effectuer une authentification complète mot de passe + OTP. Le tout premier retour après inscription/enrôlement peut ne pas encore porter les références d’une vraie exécution OTP : l’application doit alors refuser ce retour et demander une nouvelle connexion complète. Ne jamais contourner ce refus avec une valeur AMR statique.

Vérifier les cas email non vérifié, OTP absent ou faux, réutilisation de code/état, compte bloqué, session expirée et réinitialisation du second facteur. Le compte test ne devient jamais administrateur de Travaux par son email ou son rôle Keycloak.

L’organisation test exige le profil staging OIDC explicitement autorisé à l’adhésion autonome. Elle doit contenir uniquement des données fictives ; les connexions mail et l’IA externe y sont bloquées par l’application. Les organisations réelles gardent une approbation administrative. Le bootstrap de l’administrateur de Travaux est un acte d’exploitation séparé, documenté par la racine du projet.

Le dépôt Keycloak utilise Apache-2.0 ; ce dossier contient une configuration rédigée pour le projet, pas une copie de ses classes Java. Aucun agrément RGPD ou certification de cybersécurité n’est déduit de cet exemple.
