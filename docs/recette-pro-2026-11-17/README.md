# Compte, documents et assistant — recette du 17 novembre 2026

Le candidat est développé et vérifié localement. Il n’est pas publié sur le site public. Les captures utilisent exclusivement des données fictives ; aucun courrier municipal ni secret n’y figure.

## Parcours livré

La connexion et la création de compte passent par un fournisseur OIDC configuré, avec vérification cryptographique du jeton et politique de second facteur obligatoire. Après inscription, une session limitée au choix d’organisation précède tout accès métier. L’organisation test persistante contient six projets fictifs et n’ouvre aucune boîte mail. Une demande d’accès à une collectivité réelle attend son administrateur ; aucun domaine email n’attribue de rôle.

Les documents PDF, DOCX, TXT, MD et CSV jusqu’à 5 Mo sont conservés avec leur source, un reçu et un job d’analyse. Le routage est explicite : **Mistral Large4 pour l’extraction**, **GLM pour le RAG et les propositions du chatbot**. Les faits extraits restent à relire. Le RAG utilise les données autorisées et conserve ses citations.

Le chatbot peut préparer une modification de propriété, une note ou une action dans un dossier choisi. Il montre la proposition puis exige une confirmation. Le serveur contrôle auteur, droits, expiration, empreinte et révisions ; un conflit est refusé et un rejeu n’écrit pas deux fois. Les nouvelles actions rejoignent le suivi natif Yjs existant.

## Preuve avec les vraies API et données persistantes

Le [résultat navigateur](workflow-real-api.json) compte **12 contrôles réussis** dans Chrome, avec captures 1920×1080 et 390×844 : création d’un dossier, dépôt par l’interface, récupération de l’original identique, extraction en attente de validation, réponse RAG sourcée, proposition sans écriture, confirmation du statut, création d’une action et présence unique après rechargement complet. Aucune exception JavaScript ni requête échouée n’a été observée.

FastAPI, SQLite, le parseur PDF et BlockSuite/Yjs sont réels dans cette recette. **Seuls les appels de modèles sont remplacés par un transport HTTP déterministe**, qui enregistre les [identifiants réellement envoyés](model-routing.json). Le serveur utilise un mode de recette local sans authentification, distinct de la qualification OIDC. Les scénarios HTTP privés testent séparément sessions et révocations.

La suite finale comprend **563 tests Python**, **130 tests JavaScript** et **27 tests du module natif**, ainsi que les vérifications TypeScript, build, Ruff et lockfile. Voir le [manifeste de vérification](../verification-professionnelle-2026-11-17.json). Les tests d’interface avec fournisseurs simulés sont conservés dans les fichiers `frontend-*.json` de ce dossier.

Sept [régressions React dans Chrome](react-session-regressions.json) passent aussi : saisie pendant l’arrivée d’une action, changement de compte, révocation du dossier ou d’un dossier voisin, ancien état conservé par une erreur réseau, purge du vrai cache QueryClient et conservation d’un brouillon autorisé après réessai. Ces tests utilisent les composants réels avec des doubles explicitement nommés pour le contexte, le contrôleur natif et les transports. Un [contrôle négatif](react-negative-workspace.json), qui retire uniquement l’observation de session dans le bundle de test, échoue comme prévu : il prouve que la fuite de cache corrigée est détectée. Il ne s’agit pas d’un échec du paquet final. Voir les [commandes de régression](../../frontend-lovable/tests/browser/native-session/README.md) et la [recette API reproductible](../../tests/browser/README.md).

## Captures

- [Connexion et inscription](organisation-signup-1920.png) et [choix d’organisation](organisation-choice-1920.png) : vraie interface, réponses de session et d’organisation simulées ; aucun compte réel créé.
- [Document conservé](document-1920.png), [réponse RAG](rag-1920.png), [proposition avant confirmation](proposal-1920.png) et [action persistée](action-1920.png) : recette avec vraie API locale.
- [Chat sur mobile](chat-390.png).

## Activation réelle restant à qualifier

Le laboratoire Keycloak a réellement importé son realm et démarré, mais **l’inscription, TOTP et le retour OIDC n’ont pas été qualifiés de bout en bout** : Avast a remplacé le certificat local, refusé par Python et Chrome. Aucune vérification TLS ni protection du poste n’a été désactivée. Le [compte rendu exact](../RECETTE_KEYCLOAK_LOCALE_2026-11-17.md) distingue ces étapes.

La [mise en service privée](../MISE_EN_SERVICE_PRIVEE_2026.md) et le [candidat OVH](../../deploy/ovh/README.md) donnent les paramètres réels : IdP/SMTP/MFA, modèles et clés Mistral, applications OAuth, consentement DSI, clés de coffre séparées et HTTPS. Aucun conteneur ni serveur OVH n’a été déployé. La conformité RGPD reste une démarche de la collectivité avec son DPO/DSI ; ce lot ne constitue pas une certification. La sauvegarde chiffrée hors site, la restauration et le dispositif antivirus/quarantaine de production restent à réaliser avant un usage municipal réel.
