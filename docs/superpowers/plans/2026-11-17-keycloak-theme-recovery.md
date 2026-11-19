# Formulaires Keycloak MayorTech et récupération

Exécution autorisée par la racine : conserver les formulaires officiels Keycloak pour login, inscription, récupération et TOTP ; aucune collecte de mot de passe par le portail Travaux. Aucun déploiement ni SMTP dans ce lot.

- [ ] Tests rouges du nouvel intent `recovery`, de `reset_url` HTTPS/hôte/port autorisés, du fingerprint et du login_hint email borné/refusé avant réseau.
- [ ] Implémenter uniquement `oidc.py` : env `TRAVAUX_OIDC_RESET_URL`, propriété `recovery_available`, `start(intent,login_hint='')`, schéma HTTP strict. Le hint ne rejoint aucune table ni token ; mêmes PKCE, nonce, état unique, signature et MFA au callback.
- [ ] Thème `mayortech/login` parent `keycloak.v2` : CSS et logo SVG originaux, aucune copie FTL/JS/font de Keycloak, aucune ressource distante. Les formulaires natifs restent propriétaires des champs secrets et messages.
- [ ] Packager JAR standard avec métadonnées Keycloak, liste fermée de fichiers du thème, refus des liens et des collisions ; vérifier le contenu de l’archive créée.
- [ ] Vérifications ciblées et documentation d’activation opérateur : SMTP non configuré, aucun email envoyé, recette réelle du thème/IdP non prétendue.

Contrat racine : `auth.start` accepte `{intent:'login'|'signup'|'recovery',login_hint?:string}` ; propriété `.recovery_available` pour DTO public. Endpoint de reset officiel : `/realms/<realm>/protocol/openid-connect/forgot-credentials` ; les endpoints internes login-actions ne sont pas exposés comme point d’entrée.
