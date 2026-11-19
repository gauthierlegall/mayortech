# Connexions et agendas — état du lot 0.6

Ce lot prolonge le backend existant. Il n’utilise aucune messagerie municipale réelle pour ses tests et n’active aucun compte externe dans la démonstration publique.

## Code libre réellement utilisé

| Brique | Version / licence retenue | Code lu et appels intégrés |
| --- | --- | --- |
| [python-caldav](https://github.com/python-caldav/caldav/tree/v3.7.0) | 3.7.0 ; choix Apache-2.0 de la double licence | `davclient.py`, `collection.py`, `base_client.py` : découverte du principal et des agendas, requêtes REPORT et expansion des récurrences côté serveur. Le client maintenu reste chargé du XML/WebDAV et de l’authentification. |
| [icalendar](https://github.com/collective/icalendar/tree/v7.3.0) | 7.3.0 ; BSD-2-Clause | `cal/calendar.py` et son parseur : lecture/génération réelles via `Calendar.from_ical`, `Event`, `Calendar.to_ical`. Aucun parseur ICS artisanal. |
| [exchangelib](https://github.com/ecederstrand/exchangelib) | dépendance Exchange déjà verrouillée ; BSD-2-Clause | `folders/collections.py`, `util.py`, `protocol.py` : CalendarView et lecture Exchange. Réutilisation de `EWSReadOnlyCollector`, `EWSIncrementalCollector` et du store de checkpoints déjà présents dans Travaux. |
| [pyca/cryptography](https://github.com/pyca/cryptography) | 50.0.2 ; Apache-2.0/BSD | `fernet.py` : recette Fernet existante, chiffrement authentifié du dictionnaire de secrets, enveloppe liée au tenant. Pas de chiffrement inventé. |

Les [licences](third-party/calendar/) ont été conservées. Les distributions installées conservent aussi leurs notices dans leurs répertoires `.dist-info/licenses`. Les versions et empreintes de distributions sont épinglées dans `uv.lock`.

Empreintes SHA256 des fichiers effectivement inspectés dans les versions installées :

| Fichier | SHA256 |
| --- | --- |
| caldav/davclient.py | `3ac101aec43e1bb64ea76423a837b86ddff9043251dd3dc3de27a6863a87baf7` |
| caldav/collection.py | `3e11c0611397f2a4d3d06643874da8f31efb719d8baa5d5e845045ffcc353166` |
| icalendar/cal/calendar.py | `934f7f4da664f27a491526bf1524a5c47055653a7d437756db8f81b62682d89c` |
| exchangelib/folders/collections.py | `b41c8fc69c1db2869bd64e3a12859689d7aea65aa88fb5675f089c86eaa92c91` |
| cryptography/fernet.py | `dac2c23ce99e8e13956ee75c4b742c3353c8b876f109e45c46d5a49dc437982a` |

## Comportement livré

Une connexion Exchange ou CalDAV commence par une configuration administrateur enregistrée côté serveur, avec secret chiffré. Son état reste `not_tested` avant un véritable test réseau. Le test découvre le calendrier principal et la réception Exchange, ou les agendas CalDAV accessibles. L’utilisateur choisit ensuite explicitement les agendas/dossiers autorisés ; une nouvelle découverte n’élargit pas cette sélection automatiquement.

La synchronisation d’agendas lit une période fermée d’au plus 366 jours et au plus 1 000 rendez-vous. Elle conserve les identités distantes, les heures/fuseaux et les dates de fin exclusives des journées entières. Les événements sans heure de fin n’acquièrent pas une durée inventée d’une heure. Le fuseau municipal par défaut est Europe/Paris ; les fuseaux présents dans les sources sont conservés.

Le cache local garde les versions et l’historique des rattachements. Une nouvelle lecture peut mettre à jour un événement et archiver son indisponibilité, mais ne remplace jamais son rattachement humain à un chantier. Réduire la sélection ou déconnecter le compte masque les agendas concernés dans les vues courantes. Les historiques déjà collectés restent conservés pour une politique de rétention à définir avec la mairie.

L’import ICS conserve les octets originaux et leur empreinte. Il ne développe jamais une récurrence non bornée : les occurrences présentes sont affichées et une limite explicite est retournée. L’export représente les rendez-vous affichables dans la période demandée ; il ne recrée pas une série complète à partir de sa seule première occurrence. Les `RECURRENCE-ID` conservent leur type DATE ou DATETIME, y compris leurs variantes avec TZID et à heure flottante ; une journée entière n’est jamais transformée en occurrence à minuit.

Pour remplacer une occurrence dans un agenda ICS déjà importé, le fichier doit porter un `SEQUENCE` supérieur, ou le même `SEQUENCE` avec deux `DTSTAMP` comparables et celui du nouveau fichier strictement plus récent. Un rejeu identique est sans effet. Une version antérieure ou une différence de contenu à version égale est refusée atomiquement pour tout le fichier. En l’absence de version permettant d’ordonner deux contenus différents, l’application refuse de deviner lequel est le plus récent. `SEQUENCE` et `DTSTAMP` sont préservés à l’export ; un ancien fichier ne peut donc plus ressusciter silencieusement une annulation.

La collecte de mail Exchange utilise le chemin existant d’ingestion durable : source, original, pièces et jobs sont enregistrés avant avancement du checkpoint. Un échec ou une révision de connexion périmée arrête la collecte sans marquer le message distant comme lu ni avancer silencieusement son curseur. La réception et le calendrier ont des actions de synchronisation et des dates de dernière réussite distinctes. Aucune méthode d’envoi SMTP/EWS ni de modification distante d’un rendez-vous n’est exposée.

## Configuration privée

Les connexions réelles exigent `settings.auth_required`, un acteur autorisé `organization.write` et une politique serveur indépendante des champs du formulaire :

```text
TRAVAUX_CONNECTOR_EGRESS_APPROVED=true
TRAVAUX_CONNECTOR_ALLOWED_HOSTS=exchange.example.org,caldav.example.org
TRAVAUX_CONNECTOR_PRIVATE_HOSTS=exchange.example.org
TRAVAUX_CONNECTOR_ALLOWED_PORTS=443
TRAVAUX_CONNECTOR_SECRET_KEY=<clé Fernet générée et conservée côté serveur>
```

Les hôtes privés sont admis seulement s’ils sont nommés explicitement. Les adresses locales, link-local/métadonnées et multicast sont refusées. Le client CalDAV contrôle chaque requête et redirection, garde TLS activé, n’utilise pas les proxys d’environnement, refuse les méthodes d’écriture et borne les réponses à 4 Mo. Ses requêtes sont limitées dans le temps. Avec le SDK 3.7, `server_expand=True` seul ne coupe pas l’expansion cliente : le wrapper emploie aussi `expand=False`, `split_expanded=False`, `post_filter=False` et `compatibility_workarounds=False`. Le REPORT demande bien une expansion serveur, mais aucun moteur de récurrence n’est lancé localement. Si le serveur retourne encore une RRULE, la synchronisation s’arrête avec une explication et le cache précédent reste inchangé. Ce chemin est vérifié avec le véritable SDK installé et un espion interdisant tout appel à `recurring_ical_events.of`, sur une règle SECONDLY couvrant plusieurs mois.

Le coffre utilise la clé d’environnement si elle existe, sinon un fichier `.connector-vault.key` voisin de la base, créé seulement au premier besoin dans un espace protégé. Ce fichier doit recevoir les droits du service et être sauvegardé séparément avec une procédure opérateur : perdre la clé empêche le déchiffrement des comptes enregistrés. Les tables ne contiennent jamais le mot de passe en clair ; les DTO n’en exposent ni la valeur ni le ciphertext. Les journaux de débogage TLS `SSLKEYLOGFILE` / `QUICLOGDIR` et `PYTHON_CALDAV_COMMDUMP` sont refusés avant raccord institutionnel.

Choix de confidentialité issu de la lecture effective du SDK : `caldav.lib.vcal.fix()` peut écrire un diff complet du calendrier au niveau WARNING lorsqu’il répare un composant. Les loggers des SDK CalDAV et exchangelib sont donc isolés à la frontière du connecteur, avec un NullHandler sans propagation. Les diagnostics API de l’application restent génériques et les autres loggers applicatifs restent actifs. Un test `caplog` utilise un ICS réparé par le vrai SDK et un jeton factice pour vérifier qu’aucun des deux ne parvient aux journaux.

La connexion d’un compte réel et les autorisations effectives du compte technique restent à qualifier avec la DSI. Les contrôles de ce lot ne constituent pas une qualification RGPD ou une garantie globale contre une infrastructure DNS compromise ; une politique réseau sortante de l’hébergement complète le périmètre applicatif.

## Google et Microsoft 365

Les choix Google Agenda et Microsoft 365 sont présentés comme **OAuth non activé sur ce serveur**. Cette version ne contient pas de callback OAuth qualifié et ne devient pas capable d’une connexion OAuth par le seul ajout d’un client ID. Elle fournit un état honnête de configuration préalable, l’import/export ICS et les connecteurs Exchange local/CalDAV effectifs.

La suite doit utiliser les bibliothèques officielles et enregistrer les applications, scopes de lecture, URLs de retour, rotation et révocation des tokens. Sources primaires consultées : [Google OAuth serveur](https://developers.google.com/identity/protocols/oauth2/web-server), [CalendarList](https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list), [Events](https://developers.google.com/workspace/calendar/api/v3/reference/events/list), [Microsoft OAuth avec PKCE](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-auth-code-flow), [Microsoft calendarView](https://learn.microsoft.com/en-us/graph/api/calendar-list-calendarview?view=graph-rest-1.0).

## Contrats et fichiers

- `connection_hub.py` : `register_connection_routes(...)`, coffre, politique réseau, état, sélection, collecte mail et progression de première connexion privée.
- `calendars.py` : `register_calendar_routes(..., hub=...)`, import/export ICS, synchronisation de cache et rattachement humain.
- `integrations/calendar_readers.py` : adaptateurs SDK sans opérations d’écriture distante.
- `GET /api/v1/integrations` ; `POST /integrations/connections` ; `POST /integrations/connections/{id}/probe` ; `PUT /.../selection` ; `POST /.../sync` ; `POST /.../sync-mail` ; `POST /.../disconnect`.
- `GET /api/v1/calendars` ; `GET /calendars/events?project_id=&start=&end=` ; `POST /calendars/import-ics` ; `PATCH /calendars/events/{id}/assignment` ; `GET /calendars/export.ics`.
- `GET/PATCH /api/v1/onboarding`. En public, seul GET fonctionne et indique `persist_in_browser=true` ; aucune progression d’un visiteur n’écrase celle des autres.

`CalendarService.seed_demo(tenant)` est un appel opérateur explicite, idempotent et réservé aux projets ayant des sources marquées fictives. Aucun amorçage automatique et aucun endpoint public d’import de fichier privé ne sont ajoutés.

Tests : `tests/test_connection_hub.py`, `tests/test_calendars.py`, `tests/test_calendar_readers.py`, `tests/test_calendar_http.py`. Ils couvrent le coffre, la séparation des tenants/droits, les limites réseau, les sources originales, les révisions et la non-duplication des mails avant checkpoint.
