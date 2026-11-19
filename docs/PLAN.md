# Pilote Travaux — réalisation directe

Ce projet est réalisé ici. Aucun composant Antigravity n'est requis.

Objectif : un poste pour le responsable des travaux, puis un pilote institutionnel. AppFlowy reste le vrai espace de pages/blocs/bases ; l'application fournie complète la revue des preuves et le suivi des traitements. Elle ne remplace pas l'éditeur natif.

1. Construire le moteur durable : sources immuables, rattachement par référence/fil, revue des ambiguïtés, faits avec preuves, notes humaines, révisions et résumés approuvés sur leur contenu exact.
2. Construire les connecteurs : EML puis Exchange en lecture, extraction limitée, LLM structuré et sortie réseau explicitement autorisée, AppFlowy sous contrat d'API vérifié.
3. Réaliser les écrans de suivi, import, mémoire, revue et récapitulatif, y compris erreurs et petits écrans.
4. Tester la chaîne avec des données entièrement fictives, les conflits, l'isolement des accès, les redémarrages, les erreurs et l'injection indirecte.
5. Livrer les commandes de lancement, sauvegarde/restauration, conteneur et exigences du pilote. Les comptes mairie, la licence AppFlowy et les ressources OVH ne sont pas disponibles dans cet environnement.

Décision de stockage du pilote : SQLite transactionnel sur un seul hôte, un seul service et un volume persistant. Le SaaS multi-instance nécessitera PostgreSQL et une nouvelle validation de l'isolation ; aucun déploiement multi-instance n'est revendiqué ici.

Critère principal : un deuxième mail du même chantier enrichit son contexte durable sans perdre une note manuelle, toute proposition conserve une citation vérifiable, et une modification après approbation impose une nouvelle validation.
