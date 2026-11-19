# Préparation Hetzner — Implementation Plan

Goal : publier uniquement une démonstration fictive authentifiée, après recette frontend/native verte.
Architecture : archive fermée et vérifiée, image par release, un conteneur Python, volume propre, réseau Caddy existant. Le proxy existant est rechargé gracieusement après validation ; aucun autre service n'est recréé.
Tech Stack : Python3.11 standard, SSH strict, Docker Compose, Caddy partagé.
Spec : instructions de déploiement du projet, cible `/opt/apps/travaux-mairie`, domaine `travaux.kerforge.com`.

Contraintes : aucun accès institutionnel, `staging` + LLM `demo` + egress désactivé ;768MiB et0,75CPU ; aucun secret transféré depuis le projet ; owner.json lu uniquement côté exploitant. Aucun déploiement exécuté pendant cette préparation.

1. Tests avant code : archive exclut secrets et liens ; feu vert lié aux hashes ; DNS refuse toute collision ; échec Caddy restaure uniquement sa route ; restauration concurrente refusée.
2. `common.py` : noms autorisés, inventaire/hashes, manifeste, extraction vérifiée et activation atomique de la route.
3. `deploy.py` : plan/package, attestation de recette, SSH/preflight, DNS create-only explicite, exécution et récupération privée des accès hors projet.
4. `remote.py` : vérifications de propriété, répertoire réservé, génération de secret, build/version, démarrage de sa seule app, validation/reload et retour arrière.
5. `compose.yaml` et `dockerignore` : limites et environnement figé ; documentation de procédure, limites et rollback.
6. Vérifier tests unitaires et compilation. Inspection distante uniquement en lecture ; build/runtime/publication laissés au root après recette.

Review Focus : chemins symlink/traversal, sorties sensibles, collision DNS/image/volume/service, modification concurrente Caddy, échec après démarrage et compatibilité des données lors d'un retour arrière.
