# Publication du 17 novembre 2026

La release **20261117T203341Z-ee169c** est publiée sur [Travaux](https://travaux.kerforge.com/). Le serveur sert le même HTML, JavaScript et CSS que le paquet vérifié localement. App et worker sont sains ; Caddy a validé sa configuration et rechargé la route. Le contrôle indépendant confirme la sauvegarde SQLite prépublication présente et intègre.

Les tests prépublication passent : **569 tests Python**, **133 tests JavaScript** et **27 tests du module natif**, puis build TypeScript/Vite. Le contrôle navigateur en vrai mode public passe localement (24 contrôles), puis sur le site HTTPS publié (**23 contrôles**, hors accès direct au marqueur SQLite local). Les captures Full HD et mobile ont été inspectées. Aucun texte décoratif « Tout est enregistré », polling de sauvegarde à 400 ms, exception JavaScript ou requête tierce n’a été observé.

Le séparateur de la messagerie redimensionne la liste et la lecture ; le popup assistant, la question sourcée, l’enregistrement/relecture Yjs et le récapitulatif ont aussi été vérifiés. Les écritures de recette utilisent uniquement un nouveau dossier et des textes explicitement fictifs.

La [revue de compatibilité](../REVUE_MIGRATION_PUBLIQUE_2026-11-17.md) a autorisé uniquement les empreintes backend exactes de cette mise à jour publique : les 44 tables précédentes et leurs données sont conservées, 14 tables sont ajoutées, et l’ancien backend redémarre avec la même base. Le garde refuse encore tout autre code backend, dépendance, ancienne release ou contrat privé. La sauvegarde et les probes avant bascule sont conservés.

## Preuves

- [Contrôle HTTPS et sauvegarde](deployment-probe.json), [reçu de publication](apply-result.json) et [23 contrôles navigateur](checks.json).
- [Messagerie et séparateur](1920-01-public-mail.png), [assistant Full HD](1920-02-public-assistant.png), [assistant mobile](390-03-public-assistant.png).
- [Action native persistée](1920-04-public-native-action.png), [récapitulatif](1920-05-public-recap.png), [messagerie mobile](390-06-public-mail.png).
- [Manifeste de vérification](../../verification-production-2026-11-17.json).

La validation TLS distante reste active. Playwright emploie le magasin de certificats Windows existant via `--use-system-ca` ; aucune CA n’a été installée ni validation désactivée. Le probe HTTPS indépendant vérifie également le certificat et les empreintes des fichiers servis.

## Périmètre du site

Le site reste une **démonstration publique sur données fictives**. Aucun compte municipal, service OIDC/MFA réel, appel Mistral réel ou envoi n’est activé. Les imports de fichiers/courriels et les connexions externes réelles restent refusés côté serveur. La configuration privée demeure décrite dans la [notice de mise en service](../../MISE_EN_SERVICE_PRIVEE_2026.md), sans certification RGPD revendiquée.
