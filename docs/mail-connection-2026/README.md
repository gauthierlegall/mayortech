# Relier sa messagerie — version 0.8

Rapport de la livraison initiale 0.8. Le [correctif 0.8.1 et la recette Full HD](../mail-workflow-fullhd-2026/README.md) documentent les retours de parcours et les compteurs corrigés dans la version actuellement publiée.

Le parcours de raccordement suit quatre étapes : **Messagerie → Compte → Accès → Terminer**. Il est accessible par **Relier ma messagerie** dans Messagerie, depuis Connexions et dans la première utilisation. Il conserve les composants, DM Sans et les couleurs de la référence Lovable.

Version publiée le 16 novembre 2026 sur [travaux.kerforge.com](https://travaux.kerforge.com/#/connexions), release `20261116T094932Z-306a53`. Application et worker sains ; certificat TLS et empreintes du client et du moteur natif vérifiés sur le site publié.

## Parcours réel

1. Choisir Exchange, seule messagerie raccordable dans cette version. Microsoft 365 OAuth et Gmail restent explicitement indisponibles.
2. Renseigner l’adresse professionnelle, le mot de passe et l’adresse EWS du serveur. L’identifiant différent et le nom affiché sont des options. Le bouton enregistre puis vérifie ; un compte enregistré n’est pas annoncé comme vérifié.
3. Choisir uniquement les dossiers découverts par le test. La sélection conserve les agendas déjà autorisés et utilise la révision retournée par le serveur.
4. Relire le compte et le périmètre, puis lancer explicitement un premier passage. Un résultat partiel propose de continuer ; les changements acquittés ne sont pas présentés comme un nombre de nouveaux mails. La reprise historique reste facultative.

Les profils existants peuvent reprendre leur configuration. Un test échoué réutilise le profil créé. Une réponse de création perdue demande d’actualiser les comptes avant une nouvelle tentative ; aucun POST n’est rejoué automatiquement, le mot de passe est effacé. Les conflits conservent les dossiers encore disponibles pour une nouvelle confirmation après actualisation.

Les mots de passe ne rejoignent ni URL, ni stockage navigateur, ni rapport. Un changement d’accès pendant une requête bloque les étapes suivantes et les réponses tardives. La connexion réelle exige toujours un espace protégé, les droits administrateur et l’autorisation serveur existante ; le parcours ne remplace pas ces contrôles.

## Démonstration publique

Le même parcours est essayable avec un compte `example.invalid`, sans formulaire de mot de passe. Les choix restent en mémoire. La conclusion indique **« Aucun compte n’a été relié et aucun courriel n’a été importé »**. L’état réel des connexions reste inchangé.

## Cohérence de « Planifier une action »

Le choix global commence par un chantier vide, puis ses seules actions. Dans un dossier, le chantier ouvert est identifié et verrouillé. Le responsable est libre, suggéré à partir des données existantes, sans attribution automatique au visiteur. Les dates sont facultatives, le statut et le pourcentage restent indépendants ; retirer de la frise prépare une modification avant une sauvegarde explicite commune.

La [recette de planification](../planning-consistency-2026/README.md) détaille aussi la protection des saisies lors d’un changement de chantier ou d’action.

## Vérifications

| Contrôle | Résultat | Preuve |
| --- | --- | --- |
| Application et déploiement | 396 tests Python passent ; 55 tests de déploiement revérifiés après build | [Vérification courante](verification-0.8.0.json) |
| Frontend et domaine | 97 tests Node passent, dont 10 de raccordement et 17 de planning | [Vérification courante](verification-0.8.0.json) |
| Éditeur natif | 27 tests passent ; moteur inchangé depuis la v0.7 | [Vérification courante](verification-0.8.0.json) |
| Parcours privé | 20 contrôles sur le bundle compilé : API réelle en processus, lecteur Exchange fictif, conflit réel, lecture partielle et continuation | [Recette et captures](private-browser/RECETTE.md) |
| Démonstration locale | 26 contrôles aux trois largeurs, aucun appel de mutation de connexion | [Résultats](local/checks.json) |
| Planification locale | 27 contrôles : choix, saisies, unique PUT de modification puis restauration du dossier QA, faits préservés | [Résultats](../planning-consistency-2026/local/checks.json) |
| Démonstration mail HTTPS | 26 contrôles, trois largeurs, aucune mutation de connexion | [Résultats et captures](public/checks.json) |
| Planification HTTPS | 28 contrôles, deux chantiers et leurs responsables réels ; états natifs, faits et notes inchangés | [Résultats et captures](../planning-consistency-2026/public/checks.json) |
| Contrat HTTPS | 27 contrôles : assets exacts, version, droits publics, séparation de la base et refus des imports privés | [Résultats](public/contract.json) |

La [revue indépendante](review-checks.json) a levé une impasse après réponse de création ambiguë et vérifié le blocage d’une suite de requêtes après démontage. Les captures couvrent 1920, 390 et 320 px ; une adresse fictive longue a aussi été vérifiée sur le parcours privé à 320 px. Les compteurs décrivent des suites distinctes, pas des scénarios utilisateurs uniques.

Aucun compte municipal réel, transport d’envoi, OAuth Google/Microsoft, bot Telegram ou modèle Mistral n’a été raccordé par cette livraison. Les essais privés utilisent un lecteur Exchange fictif ; ils ne valent pas qualification d’un serveur institutionnel. Aucun test sur téléphone physique ni certification RGAA/RGPD n’est revendiqué.
