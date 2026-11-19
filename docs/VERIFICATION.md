# Vérifications de la livraison — 14 novembre 2026

**Historique du premier pilote.** La version 0.2.0 avec AFFiNE intégré dispose de résultats plus récents : [recette native intégrée](ux-benchmark-2026/integration/rapport.md), [réutilisation de code](REUTILISATION_CODE.md) et [mesures de livraison](verification-native.json). Les nombres et limites ci-dessous décrivent l'état antérieur.

Résultats exécutés sur cette version, sous Windows / Python 3.11.15 / Node 24.13.0 :

| Contrôle | Résultat observé |
|---|---|
| Pytest métier, API, sécurité, intégrations et reprise | **87 tests réussis** |
| Ruff sur src/tests/scripts/web/tests | Aucun diagnostic |
| Tests Node des frontières d'interface | **6 réussis** |
| Parcours mobile complet jusqu'au téléchargement | **11 opérations réussies**, rapport browser-flow.json |
| Rendus navigateur à 1440, 390 et 320 px | **24 écrans**, aucun débordement, erreur console ou erreur JavaScript |
| Panne réseau, ressource absente et restitution du focus | **3 scénarios réussis** |
| SDK MCP officiel 2.3, client et serveur en mémoire | Échange réellement exécuté ; service synthétique, pas une instance AppFlowy |
| Sauvegarde/restauration SQLite | Notes et file persistante retrouvées dans une nouvelle base |
| PDF/DOCX | Extraction en sous-processus ; PDF sans texte signalé OCR requis |
| Paquets Python | Sdist et wheel construits ; HTML/CSS/JS présents dans le wheel |
| Dépendances installées | 61 distributions auditées, aucun avis connu trouvé au contrôle |
| Références OCI | Empreintes des manifestes vérifiées ; couches/runtime non exécutés |
| Démonstration finale | Service HTTP vivant, six chantiers entièrement fictifs |

Les tests API/boucles asyncio et navigateur ont demandé l'autorisation technique des sockets locales dans le sandbox Windows. Ils n'ont utilisé aucun compte de mairie, secret réel ou mail réel. Les appels LLM/Exchange/AppFlowy de test sont synthétiques ou utilisent un transport contrôlé ; ils ne qualifient pas ces services en production.

Les jeux fictifs produits par la recette mutable ont été conservés séparément des six chantiers de la démonstration finale. Les captures du parcours gardent la provenance de ce jeu de recette ; les captures des 24 écrans ont été rafraîchies sur la démonstration propre.

Non exécutés : Docker, OVH, CI GitHub distante, instance native AppFlowy, serveur Exchange institutionnel, inférence Mistral distante et tests sur un téléphone physique. Les tests responsive utilisent un vrai navigateur aux dimensions mobiles ; ils ne valent pas audit exhaustif WCAG/RGAA ni validation juridique.

Les preuves sont dans [screens](screens/index.md) et [audit](dependances.md). Les commandes reproductibles et les prérequis figurent au [README](../README.md).
