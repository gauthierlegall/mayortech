# Rejoindre une organisation

L’utilisateur crée son compte personnel, vérifie son adresse et configure son second facteur. Il saisit ensuite le code fourni par l’organisation. Il n’accède à aucun dossier pendant l’attente.

Dans **Paramètres → Membres → Demandes d’accès**, un administrateur accepte ou refuse la demande. L’acceptation d’une organisation réelle donne le rôle lecteur ; les droits sur les dossiers sont attribués séparément. Un refus ou un retrait d’accès ne peut pas être annulé par une nouvelle saisie du code.

L’espace fictif actuel se nomme **Mairie test**. Son code est **MAIRIE-TEST**. L’acceptation y est automatique pour un nouveau compte authentifié, avec le rôle éditeur sur les dossiers fictifs. Elle ne donne aucun droit d’administration. Les connexions municipales réelles et l’IA métier externe y restent désactivées.

Pour une instance réelle, l’exploitant configure `TRAVAUX_ORGANIZATION_JOIN_CODE` côté serveur : 6 à 64 lettres ASCII, chiffres ou tirets, comparaison sans distinction de casse. Sans code configuré, aucune nouvelle demande par code n’est acceptée. Le code facilite la demande ; il ne remplace ni l’authentification ni l’accord de l’administrateur. Les tentatives sont limitées à dix par compte et organisation sur cinq minutes. Le code de test est disponible uniquement lorsque le profil fictif est activé.

Une instance héberge actuellement une organisation. Ce parcours ne constitue pas un annuaire global de collectivités. Après l’adhésion, l’autorisation d’accéder à une messagerie ou à un agenda reste une étape distincte, avec les droits du fournisseur et, au besoin, l’accord de la DSI.
