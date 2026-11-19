# Frontend MayorTech / Travaux

Base : archive `mayor-project-hub.zip` fournie par l’utilisateur, adaptée au backend FastAPI existant. Le runtime utilise React, TanStack Router, les composants UI/styles Lovable et les modules fonctionnels Travaux. Il n’utilise ni Supabase ni une passerelle Lovable. Le `.env` de l’archive n’a pas été extrait.

Avec Node 22 : `npm ci --ignore-scripts`, `npm run typecheck`, `npm run build`. Puis, à la racine du produit : `python scripts/package_frontend.py`. La configuration du client livré est `vite.product.ts` et `tsconfig.product.json`. Les anciens fichiers SSR, migrations et intégrations du projet exporté sont conservés comme référence, sans être importés par `src/app.tsx`.

En développement, lancer d’abord le backend sur 127.0.0.1:8766 puis `npm run dev` : le client est sur http://127.0.0.1:18766/web/product/. Le proxy ne concerne que la boucle locale. Le build publié sert le client et l’API sous le même domaine et conserve les protections d’origine du serveur.

Les listes et le kanban React lisent et modifient les mêmes lignes du document Yjs AFFiNE, par le SDK embarqué ; aucun second stockage éditable des actions n’est créé. Le moteur BlockSuite reste visible pour modifier les notes. Les brouillons publics sont locaux au navigateur et partagés entre le composeur du chantier et celui de la messagerie globale. Les droits sont décidés côté serveur par Casbin. Voir la recette 0.5 dans `../docs/lovable-fidelity-2026/README.md`.
