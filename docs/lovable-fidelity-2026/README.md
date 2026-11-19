# Fidélité Lovable — version 0.5

Release `20261115T184007Z-bd8e48`, publiée sur https://travaux.kerforge.com. [Comparaison visuelle originale / publication](comparatif-0.5.html). L’[audit initial](AUDIT.md) et ses captures 0.4 sont conservés comme état avant correction.

Le ZIP original a été lu et rendu : la passe rétablit le dossier du portail, ses métadonnées, sa photo, la proposition de report compacte et les onglets Page / Actions / Documents / Échanges. La police DM Sans variable et le bleu #1570d1 proviennent de la référence. Les anciennes données sont préservées : les nombres de dossiers et messages ne sont pas remplacés par les compteurs fixes de la maquette.

L’Assistant est distinct des récapitulatifs et répond avec des preuves exactes du dossier. Les actions ont les filtres, fiches, responsables, dates et priorités d’origine ; tableau et kanban éditent les mêmes lignes Yjs. Les notes AFFiNE passent d’un aperçu à un éditeur intégré. Les devis ont leurs versions, montants HT, aperçu PDF original et décisions humaines révisables.

Les échanges restent dans leur chantier, y compris après clic, rechargement et retour mobile. Répondre, À tous, Transférer, modèle de réponse et création d’une action sourcée sont rétablis. En démonstration les brouillons restent sur l’appareil, dans le même dossier Brouillons que la messagerie globale. Le modèle de réponse est présenté comme un texte à relire, sans appel IA. Les destinataires absents du corpus sont signalés.

## Vérifications

- 260 tests Python : 205 applicatifs et 55 de déploiement ; 72 tests Node ; TypeScript et Ruff passent.
- [27 contrôles de parcours publics](public/acceptance.json) et [15 contrôles de contrat](public/contract.json), après publication.
- [9 contrôles publics complémentaires](public/extra-workflows.json) : Assistant, aperçu original PDF et brouillons sans écriture serveur.
- [18 captures publiques et contrôles de largeur](public/captures.json), en 1920 × 1080, 390 × 844 et 320 × 760 : aucune erreur JavaScript/HTTP et aucun débordement de page dans ces parcours.
- [Devis : 7 contrôles réels](documents-qa/checks.json), dont validation v2, réponse de l’Assistant, retour en examen, conservation du budget et de la date.
- [Mail contextuel : 7 parcours](mail-context-qa/RECETTE.md), dont fermeture immédiate d’un brouillon et lien source après rechargement d’une action ; seule la ligne de recette a été retirée.
- [État des services](public/server-proof.json), [amorçage opérateur idempotent](public/operator-seed.json) et [provenance des rendus originaux](provenance.json).

La démo utilise uniquement des données fictives, sans mot de passe. La messagerie municipale, Mistral, l’envoi réel et les comptes individuels ne sont pas raccordés. Les captures mobiles sont des émulations navigateur. Cette recette ne certifie ni le RGPD ni le RGAA. La revue manuelle n’a relevé aucun blocage dans le lot ; les statuts personnalisés et la conservation du lien source des actions ont été corrigés avant publication.
