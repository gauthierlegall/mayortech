# Régressions React : identité, accès et notes

Cette recette lance le vrai React dans Chrome headless et bundle les composants **AuthGate, BlockEditor, Actions et WorkspaceProvider du projet** avec esbuild déjà présent. Le garde natif de périmètre, le cycle de préservation des panneaux, QueryClient et loadWorkspace sont les vrais modules. Aucun paquet supplémentaire n’est installé.

Les doubles sont explicites : contexte de workspace et contrôleur natif pour les cinq premiers cas ; uniquement le transport API pour les cas WorkspaceProvider 6 et 7. La projection/transport des actions, les primitives Button/Dialog et le choix d’organisation sont également simulés quand utilisés. Les captures portent cette mention. Il ne s’agit pas d’une recette OIDC, BlockSuite, d’une persistance serveur ou d’un fournisseur réel. Toutes les notes et actions sont fictives ; les requêtes extérieures à l’origine du serveur statique loopback sont bloquées.

Depuis la racine du projet :

```powershell
.\.venv\Scripts\python.exe tests/browser/native_session_regressions.py --output test-results/native-session-react-green
```

Prérequis existants : environnement Python du projet avec Playwright, Chrome installé et dépendances Node du frontend présentes. Le test démarre un serveur statique sur un port loopback libre et utilise un processus Chrome et un contexte neufs par scénario. Navigateur et serveur sont fermés en `finally`.

Les sept cas vérifient :

1. Une note saisie après la préservation initiale et pendant le rechargement est conservée quand arrivent de nouvelles actions et un nouveau nom de projet. Le contrôleur n’est pas remonté.
2. Le compte B ne récupère pas le brouillon React du compte A ; une ancienne écriture retardée pendant un export est refusée.
3. Le retrait du grant du dossier courant refuse son écriture retardée.
4. Le retrait du grant d’un autre dossier conserve la note et la capacité d’écriture du dossier encore autorisé, même après avoir chauffé le cache du voisin.
5. La vraie liste Actions masque une ancienne ligne révoquée même si le nouveau chargement échoue, tout en gardant la ligne encore autorisée.
6. Une session B observée avant un échec du chargement métier purge les données A du vrai cache QueryClient et masque l’ancien contenu derrière le garde de réessai. Le préchargement et le rechargement utilisent le vrai loadWorkspace.
7. Pour la même identité, un retrait de grant suivi d’un échec de détail masque l’ancien périmètre sans démonter les enfants. Un réessai réussi retire le dossier révoqué tout en conservant le brouillon du dossier autorisé et son montage unique.

Le résultat attendu est **7/7 verts**. Les artefacts contiennent `proof.json` avec les contrôleurs et états de cache observés, ainsi que sept captures **1920×1080**.

## Contrôle négatif

```powershell
.\.venv\Scripts\python.exe tests/browser/native_session_regressions.py --case dirty-note-during-action-reload --unsafe-lifecycle-control --output test-results/native-session-react-negative-notes
.\.venv\Scripts\python.exe tests/browser/native_session_regressions.py --case account-switch-clears-ui-and-stops-old-write --unsafe-lifecycle-control --output test-results/native-session-react-negative-key
```

Ces contrôles isolés modifient uniquement le contenu passé à esbuild pour rétablir le remount de BlockEditor sur changement actions/nom et le Fragment AuthGate sans clé. **Aucun module de production sur disque n’est modifié.** Chaque commande doit sortir en erreur sur son scénario ciblé : note effacée ou ancien brouillon A encore affiché. Le script refuse de faire ces mutations si les motifs attendus ne correspondent plus au code.

Un second contrôle reproduit uniquement l’absence d’annonce de la session B dans le bundle de test :

```powershell
.\.venv\Scripts\python.exe tests/browser/native_session_regressions.py --case session-b-read-business-failure-masks-cached-a --unsafe-workspace-observation-control --output test-results/native-session-react-negative-workspace
```

Il doit sortir en erreur : l’ancien cache A et son contenu survivent à l’échec métier B. La version normale doit au contraire les purger et afficher le garde.

Recette observée le 17 novembre 2026 : code corrigé 7/7 vert ; les deux contrôles de cycle de vie isolés reproduisent chacun leur régression attendue ; contrôle d’identité WorkspaceProvider avec un échec attendu. Un démarrage intermittent de la fixture Chrome a aussi été observé lors d’anciens essais groupés de mutations ; seuls les contrôles isolés ci-dessus servent de preuve négative. Ces preuves complètent les recettes du vrai backend ; elles ne les remplacent pas.
