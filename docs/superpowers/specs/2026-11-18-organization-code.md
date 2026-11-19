# Rejoindre une organisation avec son code

L’utilisateur crée son compte personnel MayorTech, vérifie son email et configure la 2FA. À sa première connexion, il saisit le code de l’organisation qu’il souhaite rejoindre. L’organisation accepte ou refuse sa demande. Le compte ne donne aucun accès aux dossiers avant cette décision.

Pour la démonstration actuelle, l’organisation fictive s’appelle **Mairie test**, son code est **MAIRIE-TEST** et les nouvelles demandes valides sont acceptées automatiquement comme membres éditeurs des dossiers fictifs. Les membres désactivés ne peuvent pas réactiver eux-mêmes leur accès. Les comptes, la vérification email et la 2FA restent réels. Les connexions de messagerie/agendas sont une étape distincte après l’accès à l’organisation.

Une organisation réelle conserve une validation humaine par son administrateur. L’acceptation crée un accès lecteur ; les droits par dossier sont attribués séparément avec la gestion existante. Le refus est explicite dans l’interface. Aucune notification email supplémentaire n’est envoyée par ce lot.

Ce lot conserve le tenant de l’instance, sa base et ses habilitations. Il ne crée pas de registre public de toutes les collectivités et n’introduit pas de changement d’organisation à partir d’un identifiant fourni par le navigateur.

## Contrat

- Code normalisé avec espaces extérieurs retirés et majuscules ; caractères ASCII alphanumériques et tirets, 6 à 64 caractères. Comparaison côté serveur en temps constant. Les tentatives sont bornées par compte vérifié avec `SessionStore.allow_attempt` et une clé dédiée.
- `Settings.organization_join_code`, chargé depuis `TRAVAUX_ORGANIZATION_JOIN_CODE`, configure le code de l’instance réelle. Le code de test par défaut est disponible seulement avec le profil fictif `test_organization_self_join`.
- `GET /api/v1/account/organizations` reste limité au compte courant ; états `not_joined`, `pending`, `rejected`, `joined`. Un `test_join_code` facultatif peut aider la démonstration et ne paraît que dans le profil test.
- `POST /api/v1/account/organizations/join`, corps `{code}`, valide le code puis renvoie `{status, organization, message}`. `status` vaut `joined`, `pending` ou `rejected` ; une session d’espace n’est émise que si l’accès est accordé.
- Le chemin historique `/account/organizations/{organization_id}/join` conserve l’entrée des membres déjà autorisés. Une nouvelle adhésion exige aussi le code sur ce chemin : un identifiant d’organisation seul n’accorde rien.
- `GET /api/v1/organization/join-requests` est réservé à un membre administrateur actif du tenant. Réponse `{items}` ; chaque élément expose `actor_id`, `display_name`, `email`, `status`, `revision`, `requested_at`.
- `POST /api/v1/organization/join-requests/{actor_id}/decision`, corps `{decision: "approve"|"reject", expected_revision}`, est réservé au même administrateur. Réponse `{status: "joined"|"rejected", member_id}`. Une décision concurrente périmée est refusée. Aucune attribution de rôle administrateur ou de dossiers réels n’est implicite.
- Les décisions, changements de membre et sessions sont cohérents en transaction ; les droits, l’email vérifié et la MFA ne viennent jamais d’un champ du navigateur. Ni code d’organisation brut, ni jeton ne sont journalisés.
- L’interface propose le formulaire « Rejoindre une organisation » avec « Code de l’organisation » et « Rejoindre l’organisation », puis une attente/refus explicite. Les membres déjà acceptés peuvent « Ouvrir cet espace » sans nouvelle demande.
- L’administration présente « Demandes d’accès », avec « Accepter » et « Refuser », dans les paramètres des membres ; gestion des rôles et dossiers existante conservée.

