# Action native de définition du mot de passe

Le 18 novembre, la sonde de lecture a trouvé `UPDATE_PASSWORD` absente du realm MayorTech. Les formulaires initiaux réels sont corrects : avec email vérifié exigé, Keycloak 26.8.2 diffère la définition du mot de passe après la validation d’adresse. Notre liste d’actions importée ne contenait que `VERIFY_EMAIL` et `CONFIGURE_TOTP` et doit aussi enregistrer l’action native de définition du mot de passe.

Le correctif conserve la vérification email et le vrai MFA. Il ajoute uniquement `UPDATE_PASSWORD`, activée, non imposée à chaque connexion, priorité 15, entre email (10) et TOTP (20). Il n’active pas l’option dépréciée qui recueille le mot de passe avant de vérifier l’adresse.

Plan d’exécution autorisé par la racine :

1. Test rouge du contrat du modèle et du helper, puis implémentation et tests verts.
2. Lecture du realm, actions et exécutions/configurations de flux, empreinte fraîche ; aucune valeur secrète dans la sortie.
3. Revue indépendante du helper et de son empreinte. L’application reste exécutée par la racine.
4. Sauvegarde serveur 0600 puis comparaison de l’état observé, enregistrement par l’endpoint officiel si nécessaire, et PUT exclusivement sur `required-actions/UPDATE_PASSWORD`.
5. Vérification que les autres actions, flux et propriétés observables du realm sont inchangés. La comparaison ne prouve pas la valeur d’un mot de passe SMTP masqué par l’API ; le périmètre des écritures n’atteint jamais SMTP.
6. Recette d’un seul compte synthétique `.invalid`, pré-vérifié pour la fixture, action native de mot de passe puis TOTP et connexion MFA complète. Cela ne teste aucune livraison d’email. Suppression/révocation en fin de recette.

Le helper refuse les dérives entre plan et écriture, sérialise ses propres opérations avec un verrou local et sauvegarde l’état avant toute écriture. Une compensation ne touche que l’action qui correspond encore exactement à la dernière écriture confirmée de cet opérateur ; une modification concurrente d’une autre action ou d’un flux n’est jamais écrasée. L’API Keycloak ne fournit pas de transaction CAS couvrant plusieurs appels : un timeout d’écriture reste un état à vérifier par un nouveau plan, pas une promesse d’atomicité.

Commande de lecture : `python deploy/private-site/required_action.py plan`. L’application exige `apply --reviewed-fingerprint <empreinte fraîche revue>` ; aucune exécution `apply` n’a été faite par l’auteur de ce correctif.

Sources primaires au tag exact : [RegistrationPassword](https://github.com/keycloak/keycloak/blob/26.8.2/services/src/main/java/org/keycloak/authentication/forms/RegistrationPassword.java), [actions applicables](https://github.com/keycloak/keycloak/blob/26.8.2/services/src/main/java/org/keycloak/services/managers/AuthenticationManager.java), [endpoints d’administration natifs](https://github.com/keycloak/keycloak/blob/26.8.2/services/src/main/java/org/keycloak/services/resources/admin/AuthenticationManagementResource.java).
