# Sauvegarde chiffrée avec restic

Ce document décrit un module d’exploitation **prévu, non implémenté**. Le travail a été suspendu au stade de conception pour traiter en priorité l’inscription, la double authentification et l’entrée dans l’organisation test demandées par l’utilisateur. Aucun binaire restic ni dépôt n’a été créé et aucune sauvegarde n’a été réalisée par ce lot.

Le contrat prévu est une copie SQLite créée avec l’API de sauvegarde cohérente, contrôlée avant son transfert et supprimée après l’opération. Le fichier unique du snapshot serait `/travaux.sqlite3`. La restauration devra exiger un identifiant complet, les tags exacts d’application/format/tenant et une nouvelle cible. Les mots de passe et identifiants de stockage ne devront pas figurer dans les arguments ni les résultats publics.

Références : [installation officielle](https://restic.readthedocs.io/en/stable/020_installation.html), [sauvegarde stdin et codes de retour](https://restic.readthedocs.io/en/stable/040_backup.html), [restauration d’un fichier précis](https://restic.readthedocs.io/en/stable/050_restore.html), [release officielle 0.19.1](https://github.com/restic/restic/releases/tag/v0.19.1).

La documentation détaillée et les résultats de recette restent à réaliser après reprise de ce sous-lot.
