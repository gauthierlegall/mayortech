# Conversations, recherche documentaire et notifications

Cette brique réutilise le moteur SQLite FTS5/BM25 et le sélecteur de passages Mistral déjà présent dans Travaux. Elle conserve les échanges dans un même fil privé et peut les relier à un bot Telegram. Aucun compte Telegram réel, message municipal ni appel LLM payant n’a été utilisé pour la recette.

## Choix open source et code lu

| Brique | Lecture et réemploi effectif |
| --- | --- |
| [SQLite FTS5](https://sqlite.org/fts5.html) | Moteur BM25 natif de SQLite, utilisé sans réécrire le classement. Requête MATCH/BM25 de la documentation adaptée dans `src/travaux/retrieval.py`. L’index temporaire contient uniquement les documents déjà autorisés ; les statistiques de classement ne mélangent pas les communes. SQLite et sa documentation sont [dans le domaine public](https://sqlite.org/copyright.html). |
| [Haystack BM25Retriever](https://github.com/deepset-ai/haystack/blob/4b4346b6d798338d9b43e70115006494012b1756/haystack/components/retrievers/in_memory/bm25_retriever.py) | Contrat de retriever, filtres et limite de résultats lus dans le code Apache-2.0. Le framework complet n’est pas installé : le pilote dispose déjà du stockage, des preuves et du client Mistral, et une deuxième base documentaire les dupliquerait. |
| [python-telegram-bot : webhook Starlette](https://github.com/python-telegram-bot/python-telegram-bot/blob/41e3633bd1b4e51693ee57059828a59a9773618a/examples/customwebhookbot/starlettebot.py) et [deep linking](https://github.com/python-telegram-bot/python-telegram-bot/blob/41e3633bd1b4e51693ee57059828a59a9773618a/examples/deeplinking.py) | Exemples CC0 lus pour le découplage webhook/file et l’appairage `/start`. Le principe est adapté à une file durable chiffrée et au serveur FastAPI existant. Le SDK PTB n’est pas embarqué ; le transport HTTPX appelle directement la [Bot API](https://core.telegram.org/bots/api). Aucun exemple de logging global n’a été repris : une URL Bot API contient le jeton. |
| [RAGFlow](https://github.com/infiniflow/ragflow) | Alternative étudiée pour une plateforme documentaire autonome. Non installée dans ce lot : elle introduirait un service documentaire et un modèle d’autorisation supplémentaires. |
| [ntfy auto-hébergé](https://docs.ntfy.sh/publish/) | Alternative pertinente pour de simples notifications. L’adaptateur n’est pas implémenté dans cette livraison ; aucun faux bouton de connexion n’est présenté. |

Les commits et empreintes des fichiers effectivement lus sont consignés dans [upstream-review.json](upstream-review.json). La requête BM25 est une reprise adaptée de la documentation ; le reste constitue le raccord métier au modèle de Travaux. Il n’est pas présenté comme du code Haystack ou PTB copié.

## Recherche et contexte

La recherche consulte les sources, extraits de documents, faits, notes et tableaux natifs enregistrés du chantier. Les tables de comptes, mots de passe, jetons et connecteurs sont exclues. Le modèle ne reçoit pas d’outil SQL et ne peut ni écrire une décision ni modifier les dossiers.

Chaque passage garde son identifiant de source, ses bornes Unicode et son empreinte. Un nouveau message reconstruit le contexte depuis la révision courante ; une réponse historique reste une archive datée. Les répétitions d’un même `client_id` renvoient la même paire de messages, tandis qu’un contenu différent avec cet identifiant est refusé.

Les agendas passent exclusivement par `CalendarService.events` : une collection désélectionnée ou déconnectée disparaît de la recherche. Les événements gardent une citation typée `kind: calendar`, leur identifiant, révision et empreinte de record, avec un lien `#/agenda?event=…&date=…`. Ils ne reçoivent aucun faux `source_id`. Une réimportation ou réaffectation change leur contexte sans confirmer une livraison du chantier. « Demain », « aujourd’hui », « cette semaine » et « semaine prochaine » utilisent une plage temporelle en Europe/Paris.

Le mode local affiche des passages retrouvés, pas une génération IA fictive. En configuration Mistral autorisée, le sélecteur existant peut choisir des extraits exacts des sources ; une configuration ne vaut pas preuve de connexion au modèle.

L’historique est privé par acteur authentifié. La démonstration anonyme utilise un cookie opaque HttpOnly, SameSite Strict et Secure hors boucle locale ; deux navigateurs ne partagent pas leurs conversations. La durée de conservation du chat est de 30 jours après sa dernière question, avec suppression lors des opérations du service et du worker. Le navigateur peut aussi supprimer une conversation ; son appairage Telegram est alors révoqué par la contrainte de référence.

## Telegram et consentement

Le défaut est une alerte générique et un lien authentifié vers l’outil, avec aperçu de lien désactivé. Le nom du chantier, le mail ou le texte de la réponse ne sont pas transmis dans ce mode. La conversation complète exige simultanément l’autorisation de l’organisation `content_relay_approved` et le choix utilisateur `conversation_sync`.

Une activation complète relaie les nouveaux messages web vers Telegram et les questions Telegram vers le même fil du serveur. Les messages utilisateur déjà saisis dans Telegram ne sont pas renvoyés en écho. L’activation n’expédie pas l’archive antérieure. La désactivation est relue juste avant chaque envoi ; un contenu déjà en file est remplacé par une alerte générique si l’accord a été révoqué.

L’appairage utilise un jeton à usage unique valable dix minutes, stocké uniquement sous forme d’empreinte. Seuls les chats privés avec identité expéditeur/chat cohérente peuvent s’appairer. Les groupes, fichiers et pièces jointes ne sont pas aspirés. Une rotation vers un autre bot réinitialise le curseur, la file entrante et les appairages, annule les envois anciens et exige un nouvel appairage.

Telegram reste un service externe. Sa [politique de confidentialité](https://telegram.org/privacy/eu) décrit le stockage cloud des conversations ; l’activation de ce relais ne rend pas ce service souverain et ne constitue pas une qualification RGPD de l’ensemble. Le choix d’une conversation complète est donc visible dans les réglages, sans être activé en démonstration.

## Exécution du worker

Le worker Telegram est distinct du worker d’import, qui conserve son isolation réseau. Il doit partager la base privée, les paramètres du même tenant et la clé du coffre avec l’application. Aucune commande ni variable publique ne contient le jeton du bot.

1. L’opérateur autorise explicitement `api.telegram.org` dans `TRAVAUX_CONNECTOR_ALLOWED_HOSTS`, avec `TRAVAUX_CONNECTOR_EGRESS_APPROVED=true`, dans un espace protégé `staging` ou `pilot`.
2. Un administrateur configure le bot par l’API HTTPS. `getMe` vérifie son identité ; le secret est conservé via `SecretVault`/Fernet, jamais renvoyé par un GET. Le mode polling désenregistre un éventuel webhook sans effacer ses messages en attente ; le mode webhook enregistre un secret spécifique.
3. L’utilisateur ouvre le lien d’appairage puis choisit ses notifications et, s’il le souhaite et si l’organisation l’autorise, la conversation complète.
4. Le processus opérateur exécute `python -m travaux.telegram_bridge worker --interval 5`. `--once` effectue un seul tick. Il ne doit pas être lancé avec la base publique de démonstration.

Le webhook exact `POST /api/v1/integrations/telegram/webhook` utilise le header `X-Telegram-Bot-Api-Secret-Token`. Il ne dépend pas d’un cookie de session et bénéficie uniquement de l’exception CSRF ciblée de l’application ; les modes demo/public le refusent. La requête entrante est mise en file chiffrée avant traitement par le worker.

L’[exemple Compose privé](telegram-worker.private.example.yaml) fournit un service séparé, activé uniquement par le profil `telegram`. Il utilise l’image, le volume et le fichier d’environnement de la même installation privée (tenant, hash de connexion, origine HTTPS et paramètres LLM éventuels). Le fichier d’environnement opérateur doit être protégé et ne contient pas le jeton du bot : celui-ci est enregistré par le formulaire administrateur dans le coffre. La clé `.connector-vault.key` du volume, ou la même clé `TRAVAUX_CONNECTOR_SECRET_KEY` fournie à l’application et au worker, est indispensable. Le volume public ne doit jamais être réutilisé. Le réseau du conteneur permet HTTPS ; l’adaptateur borne les appels à `api.telegram.org`, et un pare-feu de sortie opérateur peut renforcer cette restriction.

Cet exemple n’est pas démarré lors de la publication de la démo. Le worker d’import existant conserve `network_mode: none`.

Le `tick()` traite les entrées idempotentes, la recherche, les rappels des rendez-vous visibles des prochaines 24 heures et les notifications de dossier. Les messages sortants sont chiffrés dans une outbox durable. Une réponse de livraison ambiguë est marquée `unknown`, sans renvoi automatique pouvant provoquer un doublon ; le statut reste visible. Les journaux de transport sont supprimés après 30 jours par le worker. Un changement de bot borne également les polls déjà en vol à leur configuration d’origine.

## Recette

Commande : `.venv/Scripts/python -m pytest tests/test_conversations.py tests/test_notifications.py tests/test_calendar_retrieval.py tests/test_telegram_bridge.py -q`.

Les **32 tests** couvrent notamment l’isolation entre communes/navigateurs, les preuves exactes, la persistance et l’idempotence, les révisions courantes, l’agenda réimporté/réaffecté, les rappels déplacés, le worker reconstruit sans injection de services, le double accord, sa révocation, l’expiration d’appairage, les groupes, les livraisons ambiguës, les changements de bot réutilisant les mêmes numéros d’update et 35 notifications non lues traitées sur plusieurs ticks. Tous les transports Telegram sont simulés avec `httpx.MockTransport` ; aucun envoi réel n’a été effectué.
