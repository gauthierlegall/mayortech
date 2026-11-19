# Recette locale Keycloak avec identité fictive

Objectif : éprouver réellement l’inscription, la vérification d’adresse, TOTP, le contrôle des claims OIDC et l’entrée dans l’organisation test. Laboratoire jetable sur la boucle locale ; aucun déploiement distant, compte ou courrier réel.

- [x] Télécharger un JRE Temurin21 et Keycloak26.8.2 depuis les releases officielles et vérifier leurs SHA256 publiés avant extraction ; deux tentatives binaires maximum.
- [x] Préparer un répertoire privé `.local`, une CA fictive et un certificat couvrant les hôtes `.test`, sans installer la CA globalement ; processus cachés avec environnement minimal et ports loopback seulement.
- [x] Importer une copie du realm préparé avec secrets fictifs générés, SMTP sink local et client strict. Conserver l’application en staging avec données et accès fictifs seulement.
- [ ] Essayer le vrai parcours dans Chromium, sans captures des mots de passe, secrets TOTP, liens email ou tokens. Contrôler l’absence d’accès métier avant adhésion.
- [x] Produire seulement les résultats expurgés et les limites réellement observées, arrêter les PID dont le chemin a été vérifié. Selon le steering racine, conserver les données du lab privées après arrêt.

**Résultat :** import du realm et démarrage réels confirmés. Le parcours navigateur reste inachevé : Avast substitue le certificat par une autorité « Untrusted Root » ; Python/Chrome refusent correctement TLS. Aucun contournement. Voir `docs/RECETTE_KEYCLOAK_LOCALE_2026-11-17.md`.

Sources : [Temurin/Adoptium](https://adoptium.net/temurin/releases/), [Keycloak26.8.2](https://github.com/keycloak/keycloak/releases/tag/26.8.2), [Keycloak serveur](https://www.keycloak.org/server/configuration), [import](https://www.keycloak.org/server/importExport), [administration](https://www.keycloak.org/docs/latest/server_admin/index.html). La validation du digest établit la concordance avec l’asset publié ; aucune signature indépendante n’est prétendue.
