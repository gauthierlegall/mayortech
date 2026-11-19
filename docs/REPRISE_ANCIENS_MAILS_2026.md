# Reprise des anciens courriels Exchange

État : implémentation locale testée avec serveur EWS simulé, sans connexion à une messagerie réelle. La validation sur le serveur autorisé de la collectivité reste nécessaire avant usage opérationnel.

## Parcours

1. Un administrateur connecte le compte Exchange dans **Connexions**, vérifie sa disponibilité et sélectionne les dossiers autorisés. Un serveur Exchange local ou chez un prestataire est pris en charge par EWS ; Outlook est son client.
2. Il choisit une période et un sous-ensemble des dossiers déjà vérifiés. L’aperçu est local : aucune connexion réseau, aucun comptage exhaustif du serveur et aucune lecture de secret.
3. Le récapitulatif précise le compte, les dossiers, les dates inclusives, le fuseau **Europe/Paris** et la taille des lots. La création enregistre un plan durable ; elle ne lance pas sa lecture.
4. **Lancer la lecture** traite un lot de cinq changements au plus. Le client peut demander les lots suivants tant que la page reste ouverte. Fermer la page n’annule pas le lot déjà demandé ; les lots suivants nécessitent une nouvelle demande.
5. **Pause**, **Reprendre** et **Annuler** utilisent la révision courante du plan. Une reprise après retour sur la page retrouve le curseur enregistré, jamais un compteur local approximatif.
6. Les originaux importés alimentent le traitement habituel et la vérification humaine. Aucune information historique n’est acceptée automatiquement comme fait confirmé du projet.

**Annuler** conserve les courriels déjà enregistrés : l’annulation arrête la reprise, elle ne supprime pas les preuves. Un message supprimé ou inaccessible sur Exchange devient un avertissement ; il ne supprime pas un original déjà conservé dans l’outil.

## Période et progression

Les entrées `start` et `end` sont exclusivement des dates ISO `YYYY-MM-DD`. La fin est **inclusive en Europe/Paris**. Le serveur fige un intervalle UTC semi-ouvert `[début, lendemain de fin)` lors de la création ; si la fin est aujourd’hui, la borne supérieure est l’instant de préparation. Les changements d’heure sont pris en compte. Par exemple, le 30 mars 2025 correspond à `2025-03-29T23:00:00Z` → `2025-03-30T22:00:00Z`.

Le filtrage se fonde sur `datetime_received` fourni par Exchange, pas sur l’en-tête `Date` modifiable du courriel. Le MIME original n’est pas réécrit : sa date d’origine est conservée, et la date de réception serveur est stockée séparément en métadonnée de provenance.

La synchronisation initiale `SyncFolderItems` inventorie tout le dossier et ne fournit pas ici de restriction de date. La reprise peut donc parcourir des métadonnées hors période. Le lecteur demande d’abord seulement les identifiants puis la date serveur et la taille. Il demande le corps MIME uniquement pour un élément de la période et sous la limite de taille. Il revérifie la date et l’identité après la seconde lecture ; si le message a changé entre les requêtes, il est écarté ou signalé.

La progression présente des compteurs observés : éléments parcourus, originaux importés, originaux déjà présents, éléments hors période, indisponibles, mis en quarantaine, changements de lecture, lots et dossiers terminés. **Les éléments parcourus ne constituent pas un total de courriels uniques** : un inventaire peut contenir des changements et suppressions. `total` et `percent` restent `null`, sans estimation inventée. Le total exposé par la route de liste compte uniquement les plans de reprise, jamais les courriels du serveur.

## Bornes et reprise durable

- Un lot utilise au plus un `SyncFolderItems` avec `IdOnly`, cinq lectures de métadonnées et cinq lectures MIME. Pas de pagination par offset, ni de tri supposé stable.
- Limite : cinq changements, dix millions d’octets MIME par courriel et cinquante millions par lot. Un courriel trop volumineux est signalé sans import. Le SDK doit néanmoins recevoir la réponse MIME avant de contrôler sa taille effective si la taille serveur était incorrecte ; le déploiement doit conserver ses limites de mémoire et ses délais réseau.
- Un plan couvre de un à vingt dossiers déjà vérifiés. Un seul plan inachevé est autorisé par connexion ; il faut reprendre ou annuler celui-ci avant d’en créer un autre.
- Les tables `mail_backfill_jobs`, `mail_backfill_folders` et `mail_backfill_receipts` sont distinctes de `ews_sync_checkpoints`. La reprise historique ne lit ni ne remplace le curseur de synchronisation courante.
- Une réservation de 360 secondes empêche deux lots simultanés sur un même plan. Le réseau est appelé hors transaction SQL. Au retour, le statut, le jeton de réservation, son expiration et le périmètre autorisé sont revérifiés avant tout import.
- Les sources, les originaux, les tâches d’analyse, les reçus, la progression et le nouveau curseur historique sont validés dans une même transaction. Une erreur annule tout le lot ; le curseur précédent est conservé.
- Pause ou annulation pendant une lecture invalident la réservation. Le résultat réseau en cours est ensuite ignoré avant toute écriture. Un ancien worker ne peut pas écraser le résultat d’une nouvelle réservation après expiration.
- Un curseur Exchange invalide met le plan en erreur non reprenable. L’opérateur l’annule et crée une nouvelle reprise ; aucun retour silencieux au début n’est effectué.

## Déduplication et vérification

Avant chaque import, la transaction recherche un original `email` ayant la même empreinte SHA-256, pour le même tenant et la même connexion. La synchronisation courante utilise la même recherche. Les différences de métadonnées entre import historique et courant, ou le déplacement d’un même original dans un autre dossier, ne produisent donc pas un second original, une seconde source ni une seconde tâche d’analyse. La progression et le curseur du lecteur concerné avancent après cette vérification durable.

Une modification du MIME produit une nouvelle version de preuve selon le mécanisme d’import existant. Deux comptes Exchange distincts conservent leurs provenances distinctes même si leur contenu est identique. Un original non analysable est conservé en quarantaine, signalé pour vérification et ne déclenche pas d’analyse automatique.

La déduplication partagée couvre la collecte Exchange depuis le service intégré `ExchangeCalendarReader.collect_mail`. Le collecteur CLI historique séparé n’a pas été modifié par ce lot.

## Autorisation et confidentialité

Les lectures nécessitent `organization.read` ou `organization.write`. Les mutations nécessitent `organization.write` dans un espace privé protégé. La démonstration publique refuse la création et l’exécution de reprises, même si un acteur présente artificiellement ces permissions.

L’exécution et la création nécessitent l’autorisation de sortie réseau configurée par l’opérateur. Le point de terminaison respecte la politique HTTPS, hôtes autorisés et adresses privées autorisées du connecteur. Le compte, ses secrets chiffrés et les dossiers sélectionnés sont revérifiés avant chaque lot et avant son enregistrement. Une modification du compte ou du secret depuis la préparation du plan bloque sa reprise ; un changement de dossiers bloque les plans dont le périmètre n’est plus autorisé.

Les réponses API ne contiennent ni mot de passe, ni secret, ni curseur opaque, ni jeton de réservation. Les erreurs renvoient des codes et messages français contrôlés ; les exceptions réseau ne sont pas reprises dans le message utilisateur. Les journaux du SDK EWS restent neutralisés par la frontière de connexion existante pour éviter les traces SOAP contenant des courriels ou identifiants.

Le plan mémorise l’identité de l’opérateur qui le crée. Les actions suivantes sont permises aux administrateurs actuels du même tenant ; le navigateur ne choisit pas le tenant. La conservation et la purge des courriels demeurent régies par les politiques générales de l’application et de la collectivité, à qualifier avec son DPO.

## Contrat HTTP

Préfixe `/api/v1/mail-backfills`.

| Méthode et chemin | Effet |
| --- | --- |
| `GET /` avec `connection_id` optionnel | Plans du tenant, maximum 100 ; `{items,total,limit,can_manage,public_demo}`. |
| `POST /preview` | Validation locale et récapitulatif, sans réseau. |
| `POST /` | Création d’un plan `ready`, réponse 201. |
| `GET /{id}` | État durable, droits disponibles et progression. |
| `POST /{id}/run` | Traitement d’un seul lot borné. |
| `POST /{id}/pause` | Pause et invalidation du lot en cours. |
| `POST /{id}/resume` | Réactivation d’un plan en pause, en erreur reprenable ou à réservation expirée. |
| `POST /{id}/cancel` | Arrêt définitif du plan, sans suppression des originaux déjà importés. |

Corps aperçu/création :

```json
{
  "connection_id": "identifiant-du-compte",
  "folder_ids": ["identifiant-du-dossier-verifie"],
  "start": "2025-01-01",
  "end": "2025-12-31",
  "expected_connection_revision": 2
}
```

Les commandes utilisent `{"expected_revision": 0}`. Une révision périmée produit un conflit ; le client relit l’état avant une éventuelle nouvelle demande. Les statuts sont `ready`, `running`, `paused`, `completed`, `cancelled`, `failed`.

Les objets aperçu et plan exposent la période, les bornes UTC figées, `timezone`, `end_inclusive`, les dossiers, `batch_size:5`, `scan_mode:"ews_initial_inventory"`, `total:null` et `percent:null`. Le plan ajoute `progress`, `current_folder`, `revision`, `has_more`, `has_warnings`, `last_error`, `interrupted`, `can_manage`, `can_pause`, `can_resume` et `can_cancel`. Une erreur contient `{code,message,retryable}`.

## Injection de test

Le service réutilise `ConnectionHub.reader_factory(profile, secrets, policy)`. Le lecteur injecté expose `probe()`, `close()` et :

```python
def read_history_page(self, folder_id, *, sync_state, start, end, page_size):
    return HistoryPage(
        items=(HistoryItem("mail", "remote-id", "change-key", received_at, raw_mime),),
        next_sync_state="opaque-test-cursor",
        has_more=False,
    )
```

Le test utilise exclusivement des identités et mots de passe synthétiques ; aucun compte réel n’est nécessaire. `tests/test_mail_backfill.py` vérifie le service, ses transactions et la déduplication avec le vrai flux de collecte courant. `tests/test_exchange_backfill_reader.py` vérifie les appels EWS simulés, leur nombre, leur contenu et la lecture des seules métadonnées hors période.

## Provenance technique

Le lecteur s’appuie directement sur `SyncFolderItems` d’**exchangelib**, bibliothèque déjà utilisée par le connecteur, et les mécanismes de stockage existants. Aucun moteur de synchronisation ou orchestration supplémentaire n’est installé.

- [Microsoft : opération SyncFolderItems](https://learn.microsoft.com/en-us/exchange/client-developer/web-service-reference/syncfolderitems-operation) : première synchronisation sans `SyncState`, éléments paginés et lecture détaillée séparée.
- [Microsoft : synchroniser les éléments avec EWS](https://learn.microsoft.com/en-us/exchange/client-developer/exchange-web-services/how-to-synchronize-items-by-using-ews-in-exchange) : conservation du curseur par page et synchronisation initiale/courante.
- [Code/documentation exchangelib : SyncFolderItems](https://ecederstrand.github.io/exchangelib/exchangelib/services/sync_folder_items.html) : paramètres du service réutilisés par l’adaptateur.

Les tests prouvent le comportement local et les invariants du workflow, pas la compatibilité d’un serveur Exchange non encore raccordé. La connexion, les droits de dossiers, les limites du serveur et le comportement de son inventaire initial doivent être qualifiés sur le périmètre institutionnel autorisé avant activation réelle.
