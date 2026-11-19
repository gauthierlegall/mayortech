# Publication de la démonstration protégée — 14 novembre 2026

Application : **https://travaux.kerforge.com**. Release exécutée : `20261114T175746Z-024c31`, version `0.2.0`. Le mot de passe a été généré sur le serveur et remis dans un fichier privé séparé des sources, avec une ACL limitée au compte Windows de l'utilisateur. Aucun secret n'est contenu dans ce dossier de preuves.

La publication utilise le serveur existant de SaaSFactory, l'utilisateur SSH `deploy` et la vérification stricte de sa clé hôte. Elle dispose de son propre répertoire `/opt/apps/travaux-mairie`, de ses images versionnées et du volume `travaux-mairie-data`. Aucun achat de serveur n'a été effectué.

## Contrôles réellement exécutés

| Contrôle | Résultat et preuve |
|---|---|
| Image et services Linux | Construction Docker réussie ; `app` et `worker` en état sain, même release — [server-proof.json](server-proof.json) |
| Isolation d'exécution | Racines en lecture seule, UID10001, capacités retirées, aucun port publié sur l'hôte ; worker sans réseau |
| Quotas effectifs Docker | App : 768 Mio / 0,75 CPU ; worker : 256 Mio / 0,25 CPU, valeurs inspectées sur les conteneurs |
| Route et DNS | Nom auparavant absent créé dans la zone de l'utilisateur ; seule route Travaux ajoutée, Caddy validé avant rechargement ; compression activée |
| Accès HTTPS et session | Certificat vérifié, API401 déconnectée, connexion réelle, cookie Secure/HttpOnly/SameSite=Strict, session révoquée après déconnexion — [public-proof.json](public-proof.json) |
| Éditeur natif public | Saisie au clavier d'une note et d'une ligne de base, vraie sauvegarde, rechargement et conservation du même identifiant de ligne |
| Contexte du récapitulatif | Dernière note et valeur de base présentes dans le récapitulatif réellement généré côté serveur |
| Mobile public | Fiches lisibles à320/390 px, mêmes lignes natives, aucune largeur dépassant le viewport, menu fermé hors écran et inert |
| Courriels | Consultation dans la même session que les pages ; aucun appel à une messagerie institutionnelle |
| Traitement asynchrone | Tâche réellement mise en file depuis un processus distinct et terminée par le worker, une tentative — [operations-proof.json](operations-proof.json) |
| Sauvegarde/restauration | Sauvegarde SQLite en ligne, intégrité vérifiée, restauration dans une nouvelle base temporaire avec les mêmes7projets et1page ; la base active n'a pas été remplacée |

La recette publique utilise Chrome headless isolé, sans contrôler le navigateur personnel. Elle observe huit assertions principales, deux tailles mobiles, aucune erreur JavaScript ni requête externe à l'origine du produit. Le pilote local fait l'objet d'une [recette plus détaillée](../ux-benchmark-2026/integration/rapport.md). Les captures de ce dossier représentent le produit réellement servi par Hetzner, avec des données entièrement fictives.

## Adaptations révélées par le déploiement

Le moteur Docker de l'hôte ne dispose pas de Buildx. Le montage de cache BuildKit du Dockerfile a été remplacé par `uv sync --frozen --no-cache`, en conservant la construction en étapes et les images épinglées. La distribution source a aussi été corrigée pour conserver les assets natifs ignorés par Git : `uv build` construit maintenant la roue depuis cette distribution avec succès.

Caddy avait commencé sa demande de certificat avant la propagation du nouveau DNS. Après confirmation de la résolution depuis l'hôte, sa configuration inchangée a été validée puis reprovisionnée gracieusement. Les empreintes des fichiers de configuration étaient identiques avant et après cette opération ; le test HTTPS a ensuite réussi. Aucun mode TLS de la zone Cloudflare n'a été changé.

## Périmètre de cette démonstration

Le mode est `staging`, avec moteur déterministe `demo` et autorisation de sortie LLM désactivée. Aucun mail municipal, accès Exchange ou appel Mistral n'a été utilisé. Le serveur AFFiNE standalone complet n'est pas installé : son moteur documentaire libre est embarqué dans notre produit, avec ses notices et les sources MPL requises.

L'édition des bases sur téléphone, les pièces binaires natives, les relations/formules avancées et la collaboration en temps réel restent hors de cette version. L'audit npm signale encore Zod3 malgré le backport documenté. Aucun scan OS d'image, audit RGAA complet, test physique sur téléphone ni certification RGPD n'est revendiqué. L'ouverture aux courriels réels nécessite un périmètre institutionnel validé et la recette des connecteurs/fournisseurs.

Le rollback ciblé et les accès d'exploitation sont documentés dans [deploy/hetzner/README.md](../../deploy/hetzner/README.md). Cette instance n'est pas encore un SaaS municipal ouvert à plusieurs collectivités.
