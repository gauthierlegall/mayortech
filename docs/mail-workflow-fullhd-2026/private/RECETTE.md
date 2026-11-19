# Recette privée du raccordement — Full HD

Le parcours complet passe **38 contrôles**, dont **13 vérifications de dimensions PNG** et 25 contrôles fonctionnels, sur le bundle **0.8.1**, entrée `index-BAatJxwh.js`. Chaque capture mesure exactement **1920 × 1080 pixels**, sans redimensionnement ni retouche.

Les assets sont ceux du produit compilé servi à `http://127.0.0.1:8766`. Les requêtes API du navigateur sont transmises à la vraie application privée en processus : session, droits, contrôle de révision, coffre, ingestion et conservation des originaux sont exécutés. **Seul le lecteur Exchange est fictif.** Aucun serveur institutionnel, transport d’envoi ou réseau fournisseur réel n’est contacté ; cette recette ne prouve pas une connexion TLS à Exchange.

## Résultats

- Une seule création de profil, malgré un premier test volontairement échoué puis son réessai.
- Le dossier coché reste sélectionné après retour à Compte et nouvelle vérification du même profil.
- Un vrai conflit de révision est provoqué par une sélection concurrente de calendrier. Le choix mail est conservé ; l’actualisation puis la confirmation gardent le calendrier existant.
- Deux passages explicites de lecture : le premier annonce des éléments restants, le second termine ce passage. Les deux courriels fictifs sont conservés comme originaux uniques, visibles puis lisibles dans Messagerie.
- Après import, l’API compte **9 non-lus** et le rail affiche **9**. Après ouverture d’un courriel importé, l’API compte **8 non-lus** et le rail affiche **8**.
- Mot de passe fictif masqué dans les captures, absent du stockage navigateur ; aucune erreur JavaScript ni requête externe.

Les deux réponses d’erreur attendues servent la recette : échec temporaire de test et conflit de révision. Elles ne sont pas des pannes résiduelles. Les [résultats bruts](checks.json) conservent l’ordre, les réponses et les seules propriétés API non sensibles utiles à la vérification.

## Captures 1920 × 1080

| Étape | Capture |
| --- | --- |
| Choix de la messagerie | [01 — Fournisseur](01-1920-provider.png) |
| Formulaire de compte vide | [02 — Compte](02-1920-account-empty.png) |
| Saisie fictive, mot de passe masqué | [03 — Formulaire rempli](03-1920-account-filled.png) |
| Informations avancées et bouton de test | [04 — Avant vérification](04-1920-account-before-test.png) |
| Test volontairement échoué, profil conservé | [05 — Échec récupérable](05-1920-test-failure.png) |
| Accès vérifié, dossiers disponibles | [06 — Dossiers](06-1920-folders-verified.png) |
| Dossier conservé après retour à Compte | [06b — Retour vérifié](06b-1920-folders-after-backtrack.png) |
| Conflit réel de sélection et choix conservé | [07 — Conflit](07-1920-scope-conflict.png) |
| Périmètre enregistré avant toute collecte | [08 — Récapitulatif](08-1920-review-before-import.png) |
| Premier passage, suite disponible | [09 — Lecture partielle](09-1920-import-partial.png) |
| Deuxième passage effectué | [10 — Lecture effectuée](10-1920-import-complete.png) |
| Courriels fictifs importés visibles | [11 — Messagerie](11-1920-mailbox-imported.png) |
| Original fictif ouvert et compteur actualisé | [12 — Lecture du message](12-1920-imported-message.png) |

Les preuves avant correction sont conservées séparément : [compteur après import](counter-before-fix.json), [choix perdu lors du retour](backtrack-before-fix.json) et [compteur après lecture](reader-counter-before-fix.json). Les résultats courants ci-dessus décrivent leur revalidation sur 0.8.1.
