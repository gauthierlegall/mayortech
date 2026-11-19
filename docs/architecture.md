# Domaine durable du pilote local

La version 0.2.0 ajoute `workspace.py` : chaque page AFFiNE garde son état Yjs natif, son texte matérialisé, sa révision et son empreinte. L'enregistrement du document et de sa note de contexte est atomique dans la même transaction SQLite. Un conflit de révision conserve la saisie du navigateur. L'interface attend toutes les générations de sauvegarde avant une navigation, une déconnexion ou la préparation d'un récapitulatif.

Le moteur BlockSuite tourne dans la page du chantier, sous la même origine et session ; aucun serveur AFFiNE complet ni compte externe n'est nécessaire. La base native reste la source canonique de ses lignes ; la vue de cartes mobile lit les mêmes identifiants et propriétés. Cette version n'active pas l'édition de base mobile, les pièces binaires, les formules avancées, les relations entre bases ou la collaboration en temps réel.

`domain.py` contient les règles indépendantes des fournisseurs : montants EUR exacts avec `Decimal`, valeurs typées, dates ISO, citations exactes et empreintes SHA-256. `repository.py` expose des méthodes synchrones retournant des dictionnaires JSON. Le serveur fournit le tenant et l'acteur authentifiés ; ces valeurs ne constituent pas à elles seules un système d'authentification.

SQLite utilise les clés étrangères, WAL, un verrou par instance et des transactions `BEGIN IMMEDIATE`. Les décisions métier sont atomiques avec l'incrément de révision, l'événement et l'outbox. Une seconde connexion voit le résultat seulement après commit. Ce choix convient à la démonstration locale et ne qualifie pas une exploitation SaaS multi-collectivités.

Les sources sont des versions immuables dans l'API du dépôt. Le même identifiant de transport avec un contenu modifié crée une nouvelle version ; son ancien texte et son hash restent accessibles. Une citation est contrôlée par source, hash et offsets Unicode du texte exact. Une référence de chantier exacte et un fil précédemment rattaché peuvent déterminer le dossier ; des indices divergents ou un simple nom vont en revue. Le matching ne confère pas de nouveaux droits.

Les propositions ne remplacent aucun fait accepté. Un conflit sur un champ comparable exige `replace` explicitement ; les dates de livraison et de réception ainsi que les bases HT/TTC restent distinctes. Les preuves répétées sont conservées, un rejet n'est pas reproposé à chaque replay et une nouvelle annonce peut rétablir une ancienne valeur supersédée en tant que nouvelle proposition. La déduplication est déterministe : aucune déduplication sémantique n'est revendiquée.

Une note humaine est conservée séparément et devient une source identifiée comme telle. La génération ne la réécrit pas. Chaque résumé stocke le snapshot de mémoire, sa révision/hash, son texte/hash et ses citations. La génération locale par défaut est déterministe et porte son nom de modèle. Le texte d'un LLM peut être fourni avec ses citations ; les contrôles de passage exact ne prouvent pas à eux seuls que chaque phrase est sémantiquement étayée. La relecture humaine reste nécessaire.

Corriger un brouillon produit une nouvelle version. L'approbation compare les hashes de contenu et de snapshot et la révision du chantier. Si un brouillon importé depuis un outil externe porte une révision native, l'approbation doit fournir la même valeur. Ce contrôle concerne l'empreinte observée : il ne constitue pas un verrou CAS sur la page externe, dont la relecture relève de l'adaptateur. L'export d'une version validée doit lire le snapshot backend, jamais une page distante vivante. Un nouvel événement accepté rend les anciens résumés obsolètes sans modifier leur contenu validé.

`events` et `outbox` tracent les décisions et notes ; `audit_events` trace la création, l'approbation et l'annulation de résumés avec acteur et hashes. Le worker durable est un module distinct. La livraison d'une outbox n'est pas une garantie d'exécution distante exactement une fois ; l'intégration doit réconcilier les timeouts ambigus.

## Trajectoire PostgreSQL

La migration PostgreSQL n'est pas une condition légale automatique du pilote mono-utilisateur. Si elle est retenue pour le déploiement : migrations SQL versionnées ; remplacement des verrous SQLite par transactions PostgreSQL et mises à jour conditionnelles sur révision ; contraintes composites tenant/objet conservées ; `JSONB` pour les payloads, types monétaires exacts, timestamps avec fuseau ; file durable avec lease/fencing et `FOR UPDATE SKIP LOCKED` testée sur PostgreSQL. Pour tout stockage retenu avant données municipales, vérifier sauvegarde/restauration, accès aux objets, exploitation, rétention/archives et capacité sur le déploiement réel. Une suite SQLite verte ne remplace pas ces vérifications et n'est pas une certification RGPD.

Tout le corpus de développement est fictif. Aucun secret ni courrier municipal n'est nécessaire pour exécuter les tests de ce domaine.
