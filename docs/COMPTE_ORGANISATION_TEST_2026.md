# Compte personnel et organisation test

L’inscription utilise un fournisseur d’identité OIDC configuré par l’exploitant. Les mots de passe et le second facteur restent chez ce fournisseur. Travaux ne possède aucun formulaire de mot de passe ou stockage OTP maison.

1. « Créer mon compte » ouvre l’URL HTTPS d’inscription explicitement configurée. L’adresse doit être vérifiée et la politique MFA satisfaite avant de créer une session.
2. Un nouveau compte vérifié reçoit une session de quinze minutes réservée au choix d’organisation. Elle n’autorise ni consultation des dossiers, ni import, ni connexion mail, ni usage de l’assistant.
3. Sur l’instance de démonstration privée explicitement configurée en staging, « Rejoindre l’organisation test » accorde le rôle éditeur et les accès explicites aux seuls projets fictifs de cette instance. La session est renouvelée atomiquement ; le compte ne devient jamais administrateur.
4. Pour une organisation réelle, cette action enregistre une demande en attente de validation administrative. Aucun accès aux dossiers n’est accordé pendant l’attente. Un membre désactivé ne peut pas se réactiver par l’adhésion autonome.

Le mode d’adhésion test bloque les connexions mail, l’import EML réel et les sorties IA externes côté serveur. Il exige `staging`, `auth_mode=oidc`, le fournisseur IA de démonstration et aucune approbation de sortie IA. Ne jamais y importer de courrier ou de document personnel réel. La liste des organisations est bornée à l’instance ; un utilisateur ne peut pas choisir le tenant d’un autre déploiement.

L’API de session expose seulement un identifiant de compte opaque et son nom d’affichage. L’interface attend le choix d’organisation avant de charger les données métier et peut séparer son cache par cet identifiant. Les tokens du fournisseur ne parviennent pas au navigateur de l’application.

La préparation [Keycloak](../deploy/keycloak/README.md) décrit l’activation de l’inscription, la vérification d’adresse, TOTP, les claims MFA réellement produits et les URI exactes. Elle exige encore des origines HTTPS, un IdP opérationnel, une configuration SMTP approuvée et les secrets du client côté serveur. La validation de cette préparation en laboratoire doit être distinguée d’un déploiement réel ou d’une certification RGPD/cybersécurité.

Vérification du cœur du lot : 70 tests ciblés verts, dont trois tests HTTP de la vraie API pour les limites de session, l’adhésion et CSRF. Les échecs d’audit ou de création de session annulent toute activation. La recette auprès d’un vrai fournisseur demeure un contrôle distinct.

## Préparer une organisation persistante

Depuis la racine du projet et son environnement Python installé :

```powershell
.\.venv\Scripts\python.exe scripts/prepare_test_organization.py --database .local/organisation-test/workspace.sqlite3 --tenant organization-test --public-origin https://travaux.test
```

`travaux.test` est un nom réservé de recette ; fournir l’origine HTTPS exacte autorisée pour l’instance destinée à la présentation. Le script n’ouvre aucun port, n’effectue aucune connexion IdP et ne crée aucun utilisateur. Il ignore les variables TRAVAUX déjà présentes et n’ouvre aucun fichier `.env`. La base est persistante, marquée comme fictive et contient le profil « Organisation test » ainsi que les projets de présentation. Une seconde exécution pour le même tenant conserve la base et ne duplique pas les projets.

Une base non marquée, une base marquée pour un autre tenant ou un chemin indirect sont refusés. Ne jamais réutiliser une base métier réelle. Le marqueur empêche aussi de redémarrer ensuite cette base comme une organisation normale.

Pour la servir, l’exploitant configure séparément `TRAVAUX_DB` sur cette base, `TRAVAUX_TENANT` sur le même identifiant, `TRAVAUX_MODE=staging`, `TRAVAUX_AUTH_MODE=oidc`, `TRAVAUX_TEST_ORGANIZATION_SELF_JOIN=true`, `TRAVAUX_LLM=demo`, aucune sortie IA approuvée, puis les paramètres HTTPS/OIDC réels décrits dans la préparation Keycloak. Aucun mot de passe, compte administrateur, client secret ou second facteur n’est fourni par le script. Trois tests supplémentaires vérifient sa création, son idempotence et les refus de réutilisation d’une base.
