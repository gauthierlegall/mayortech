# MayorTech — démonstration travaux

## Fonctionne réellement
- Pages françaises : chantiers, dossier (Page, Actions, Documents, Échanges), actions globales, messagerie et paramètres.
- Quatre chantiers fictifs, recherche, filtres, favoris et création de dossiers et d’actions.
- Une source commune pour les actions, statut modifiable en tableau et Kanban, déplacement de cartes, échéances et responsables.
- Réception idempotente du sixième mail du portail : rattachement au chantier existant, deuxième PDF conservé, une seule action d’accès vendredi.
- Confirmation ou correction du report : date partagée, ancienne valeur, nouvelle valeur, auteur et message source dans l’historique. Le rejet conserve la date initiale.
- Deux PDF fictifs originaux téléchargeables et consultables. Version reçue en examen distincte de la version validée ; validation explicite possible.
- Véritable moteur BlockSuite 0.19.5, chargé uniquement dans le navigateur. Édition de texte et blocs natifs, état Yjs sauvegardé dans Lovable Cloud. Modification et relecture après rechargement vérifiées.
- Récapitulatifs enregistrés et versionnés, texte révisable et exportable, boutons vers les sources.
- Sauvegarde distante de l’espace fictif avec contrôle de version. Réinitialisation confirmée par l’utilisateur. Les visiteurs partagent cette démonstration publique.
- Écrans contrôlés à 1920 × 1080 et 390 × 844. Tests métier et parcours de confirmation, PDF, cohérence des actions et notes sauvegardées exécutés.

## Simulé et limites précises
- Messagerie fictive : réception de scénario, dossiers, lecture, recherche, réponse, transfert, brouillons et envoi simulé. Aucune connexion ni envoi Exchange. Les messages sont affichés individuellement ; regroupement avancé des conversations et réponse à tous avec une véritable liste de destinataires restent à compléter.
- Assistant déterministe et explicitement marqué démonstration, sans modèle IA : questions prédéfinies et résumé du dossier, pas d’analyse libre réelle ni ingestion documentaire.
- Organisation et rôles fictifs modifiables : aucune invitation réelle, authentification de production ni contrôle d’autorisation accordé par ces valeurs.
- Le modèle est un agrégat JSON versionné pour la démo, pas encore le schéma relationnel multi-organisations de production. Les dates de scénario sont fixes en novembre 2026.
- BlockSuite est intégré réellement, mais ses menus natifs ne sont pas encore tous francisés et les liens intégrés aux objets métier / téléversements natifs ne sont pas raccordés. La lecture hors éditeur affiche un aperçu statique ; les notes enregistrées sont consultables dans le moteur.
- Commentaires et historique détaillé par action, téléversement arbitraire de documents, synchronisation temps réel multi-utilisateur, analyse des contradictions et déduplication de mails réels restent à réaliser.

## Licences
Les paquets BlockSuite 0.19.5 (`blocks`, `presets`, `store`) sont sous **MPL-2.0**, et non MIT. `@blocksuite/icons` 2.1.75 est sous MIT ; Yjs sous MIT. Aucun code interne de BlockSuite n’est modifié. Conserver les notices et respecter l’obligation de disponibilité du source des fichiers couverts si distribués ou modifiés. Sources : https://github.com/toeverything/blocksuite/blob/v0.19.5/LICENSE et métadonnées des paquets installés. Validation juridique finale à prévoir avant distribution commerciale.

## Production à raccorder
- Authentification et permissions côté serveur, rôles protégés, cloisonnement des organisations et boîtes personnelles. Ne jamais mettre de données réelles dans la table publique de démonstration.
- Adaptateur Exchange à choisir après inventaire du serveur et protocoles effectivement disponibles (EWS ou IMAP/SMTP, sans supposer Microsoft 365), identifiants côté serveur, fichiers d’origine et identifiants de conversation, reprise et déduplication.
- Fournisseur IA configurable : raccordement Mistral envisagé, citations vérifiées, accès limités à l’utilisateur, extraction documentaire et validation humaine des changements.
- Hébergement OVH : adaptation du déploiement TanStack Start, sauvegardes, supervision, stockage de fichiers et secrets. Aucun déploiement OVH effectué ni conformité RGPD acquise revendiquée.