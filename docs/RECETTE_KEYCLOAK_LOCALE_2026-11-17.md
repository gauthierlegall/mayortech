# Recette locale Keycloak du 17 novembre 2026

Le laboratoire a exécuté **Keycloak26.8.2** avec un **JRE Temurin21.0.13+9** portable dans un répertoire privé `.local`, sans installation globale ni Docker Desktop. L’environnement des processus était limité aux variables système indispensables et aux secrets fictifs créés pour ce test ; aucune configuration mail/IA/IdP existante n’a été chargée.

Les deux archives officielles ont été contrôlées avant extraction :

| Archive | SHA256 publié et obtenu |
| --- | --- |
| Keycloak26.8.2 ZIP | `321ffee62ec28fab18fe885d8cd62cc814edce72a35cd062dc81b504c1a406b3` |
| Temurin JRE21 Windows x64 | `2332c0b4cff6bed722da3567c91d5e47568bcba863fa4945d0a8d6fc76158628` |

Sources : [release Keycloak](https://github.com/keycloak/keycloak/releases/tag/26.8.2), [release Temurin](https://github.com/adoptium/temurin21-binaries/releases/tag/jdk-21.0.13%2B9). La concordance des digests publiés a été vérifiée ; aucune vérification indépendante de signature n’est revendiquée.

## Ce qui a réellement été exécuté

- Import réussi d’une copie du realm préparé, conservant les flux d’inscription, email et TOTP et le mapper AMR, avec secrets et SMTP sink purement fictifs.
- Initialisation réelle de la base H2 locale et création d’un administrateur de laboratoire temporaire.
- Démarrage du serveur Keycloak et du backend Travaux staging sur des écoutes vérifiées `127.0.0.1` uniquement : HTTPS443/9443, gestion9000 et SMTP2525. Cache local sans cluster. Aucun email sortant ni utilisateur réel.
- Lancement d’un vrai Chrome headless avec profil jetable et résolution des noms `.test` limitée au processus.

## Limite observée avant inscription

La protection Avast Web/Mail Shield intercepte le TLS local et présente une chaîne signée par `Avast Web/Mail Shield Untrusted Root`, à la place du certificat signé par la CA fictive du laboratoire. La comparaison du certificat réseau au certificat local confirme qu’ils diffèrent.

Python a refusé la chaîne avec `CERTIFICATE_VERIFY_FAILED` et Chrome avec `ERR_CERT_AUTHORITY_INVALID`. Ces refus ont été conservés : aucune désactivation de validation TLS, installation de CA globale, modification d’Avast ou autre contournement n’a été effectué. L’application de production et sa politique SSRF sont inchangées ; seul un transport injecté dans le script jetable destinait les noms `.test` à la boucle locale, avec validation TLS de la CA fictive.

**L’inscription réelle, le clic de vérification d’adresse, l’enrôlement et l’exécution TOTP, puis les claims `pwd`/`otp` et le callback OIDC ne sont donc pas qualifiés par cette recette.** Leur couverture actuelle repose sur les tests unitaires et HTTP contrôlés de l’application. Le démarrage et l’import Keycloak réussis ne prouvent pas ces étapes.

Une recette complète reste nécessaire dans un environnement HTTPS autorisé dont la chaîne de confiance peut être validée sans contourner la protection du poste. Ce laboratoire ne constitue ni un déploiement de la collectivité, ni une certification RGPD ou cybersécurité.

Les PID du lanceur, du backend, du SMTP et de Java ont été arrêtés puis vérifiés absents ; les quatre ports sont libérés. Les données fictives du laboratoire restent dans leur répertoire privé, sans modification des autres processus ou services du poste.
