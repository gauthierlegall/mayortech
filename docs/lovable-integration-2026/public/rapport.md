# Version Lovable publiée

La release **20261115T113918Z-45ce06**, version **0.4.0**, est accessible à https://travaux.kerforge.com sans mot de passe dans le mode public de démonstration.

**50 contrôles de parcours et 14 contrôles de contrat passent** après publication, avec de vrais rendus 1920×1080, 390×844 et 320×760. Aucune erreur JavaScript, HTTP ou requête vers un hôte tiers n’a été observée dans ces parcours. Les brouillons de démonstration n’ont envoyé aucun corps au serveur.

Les contrôles couvrent le dernier texte enregistré avant navigation, les mêmes lignes AFFiNE entre liste/Kanban/mobile, le contexte courant du récapitulatif, le téléchargement original, la réponse en brouillon, l’isolation entre visiteurs, les couleurs persistantes, les paramètres et le focus mobile. Les imports privés sont refusés côté serveur. La base historique privée est préservée dans un fichier distinct.

L’application et son worker sont sains, avec limites mémoire/CPU, racine en lecture seule et aucun port hôte publié. Le worker ne dispose pas de réseau. La route Caddy propre au produit a été validée et rechargée.

La messagerie municipale, Mistral et les comptes individuels ne sont pas raccordés. Toutes les données du corpus sont inventées. Les captures mobiles sont issues d’une émulation navigateur ; les cellules des fiches natives mobiles restent en lecture seule.

- [Contrôles des parcours](acceptance.json)
- [Contrat et séparation des données](contract.json)
- [État des services](server-proof.json)
- [Chantiers FHD](1920-projects.png)
- [Messagerie FHD](1920-mailbox.png)
- [Kanban mobile](390-kanban.png)
