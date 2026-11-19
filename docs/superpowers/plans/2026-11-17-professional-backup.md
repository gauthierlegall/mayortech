# Sauvegarde professionnelle avec restic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sauvegarder la base SQLite cohérente dans un dépôt restic chiffré et restaurer uniquement un snapshot du tenant vers une nouvelle cible validée.

**Architecture:** Le module est réservé à l’exploitation locale, sans endpoint public. Une copie cohérente `sqlite3.backup()` est contrôlée avant transmission au processus restic ; celui-ci reçoit exclusivement une liste d’environnement autorisée. La restauration vérifie ID complet/tags/chemin, extrait un fichier connu, vérifie SQLite et le tenant, puis crée atomiquement une cible inexistante.

**Tech Stack:** Python stdlib/SQLite, CLI restic officielle (BSD-2-Clause). Aucun format cryptographique applicatif inventé.

**Spec:** Demande professionnelle du 17 novembre 2026, sous-lot sauvegarde confié par l’agent principal ; aucun dépôt existant, secret réel ou service distant utilisé pour la recette.

## Global Constraints

- Binaire et fichier de mot de passe fournis par chemins absolus explicites, sans symlinks ; aucune recherche implicite dans PATH.
- Pas d’initialisation, `forget`, `prune`, suppression ou déverrouillage forcé d’un dépôt par ces fonctions.
- Dépôts pris en charge : chemin local absolu, REST HTTPS ou S3 HTTPS explicitement fourni. Aucun backend lançant une commande auxiliaire SSH/rclone.
- Tags exacts : application, format et SHA-256 du tenant ; ID de snapshot complet de 64 caractères hexadécimaux, aucun `latest` implicite.
- Secrets de l’application jamais hérités par le processus ; informations d’accès au stockage uniquement dans `credential_env` explicitement fourni.
- Aucun appel contre un dépôt distant pendant les essais ; laboratoire fictif exclusivement sous `work`.

## Review Focus

- WAL actif : la copie doit contenir chaque écriture validée, sans copier manuellement le fichier principal seul.
- Autre tenant, autre chemin, ID abrégé ou snapshot ambigu : refus avant extraction.
- Échec enfant, mauvais mot de passe ou données altérées : aucun faux succès ni cible partielle, fichiers temporaires nettoyés.
- Cible existante ou créée pendant la restauration : refus sans écrasement.
- Logs et sous-processus : aucun mot de passe, token IdP/Mistral/EWS ou erreur brute du fournisseur exposé.

### Task 1: Copie cohérente et sauvegarde

**Files:** créer `src/travaux/professional_backup.py`, `tests/test_professional_backup.py`.

**Interface:** `backup(settings, repository, password_file, binary, *, credential_env=None, work_dir=None, timeout=900, runner=None) -> dict`.

- [ ] Écrire et observer les tests rouges pour copie WAL, refus de source/cible et environnement restreint.
- [ ] Implémenter copie SQLite en lecture seule, contrôle d’intégrité/périmètre et appel restic via fichier stdin déjà complet.
- [ ] Vérifier ID et tags du snapshot retourné ; nettoyer le staging privé dans tous les cas.

### Task 2: Restauration sans écrasement

**Interface:** `restore(settings, repository, password_file, binary, snapshot_id, target, *, credential_env=None, timeout=900, runner=None) -> dict`.

- [ ] Tester rouge tags/tenant/chemin, collision et échecs de déchiffrement ou d’intégrité.
- [ ] Vérifier le snapshot sélectionné puis `restic dump <id> /travaux.sqlite3` vers un fichier privé.
- [ ] Contrôler SQLite/tenant et publier par hardlink exclusif vers une cible inexistante ; aucun fallback qui écrase.

### Task 3: Recette restic réelle et documentation

**Files:** créer `docs/SAUVEGARDE_PRO_RESTIC_2026.md`, preuves sous `outputs/travaux-professional-2026-11-17/backup`.

- [ ] Télécharger au plus deux tentatives le binaire officiel Windows 0.19.1 ; recouper SHA-256 GitHub et SHA256SUMS avant exécution.
- [ ] Initialiser seulement un dépôt fictif dédié, sauvegarder/restaurer, tester mauvais mot de passe, collision et altération contrôlée.
- [ ] Conserver résultats et limites explicites, arrêter tout processus et retirer les données temporaires créées.
- [ ] Communiquer le contrat CLI à la racine, qui conserve la propriété de `cli.py` et de la rotation du coffre.
