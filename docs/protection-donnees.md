# Protection des données — dossier de décision du pilote

Actualisation : le [dossier Exchange/OVH/Mistral du 16 novembre 2026](cible-ovh-exchange-mistral-2026-11-16.md) précise les endpoints régionaux, le ZDR, les limites actuelles des habilitations et les preuves attendues avant données réelles.

Le code livré ne constitue ni une certification RGPD ni une autorisation d'utiliser les mails de la mairie. Le développement a utilisé uniquement des données entièrement fictives. La commune reste responsable de son traitement ; le DPO conseille et accompagne l'analyse.

Le [guide collectivités de la CNIL](https://www.cnil.fr/sites/default/files/2026-11/guide_pratique_rgpd_collectivites_territoriales.pdf) et les [questions-réponses IA générative](https://cnil.fr/fr/les-questions-reponses-de-la-cnil-sur-lutilisation-dun-systeme-dia-generative) fondent les points à documenter : finalité précise, base légale appropriée, minimisation, habilitations, information et droits des personnes, durées, registre et sous-traitance. Examiner la nécessité d'une AIPD avec le DPO ; son besoin ne se déduit pas du seul nom du modèle.

## Décisions avant données réelles

| Sujet | Décision et preuve attendues |
|---|---|
| Usage | Suivi interne des chantiers, catégories de mails autorisées et exclusions ; éviter RH/santé/signalements étrangers à la finalité |
| Autorisation | Mandat institutionnel, compte technique et accès aux seuls dossiers nécessaires |
| Fournisseurs | Contrats et sous-traitants, lieux de stockage/traitement/support, transferts éventuels, conservation et réutilisation des données |
| LLM | Endpoint/modèle exacts, absence de repli, modalités de rétention et d'entraînement effectivement contractualisées, évaluation sur corpus autorisé |
| Archives | Archiviste associé ; calendrier de conservation, versement et élimination autorisée ; restauration et copies traitées aussi |
| Sécurité | Recette HTTPS, comptes, postes mobiles, chiffrement, sauvegardes, accès support, révocation et gestion des incidents |
| Qualité IA | Citations et revue humaine, contradictions visibles, absence de décision/envoi automatique, couverture partielle explicite |

Le [RGPD, chapitre IV](https://www.cnil.fr/fr/reglement-europeen-protection-donnees/chapitre4) encadre notamment la conception, les sous-traitants et la sécurité. Les résumés peuvent eux-mêmes contenir des données personnelles ; ils ne deviennent pas anonymes parce qu'ils sont courts.

## OVH et attentes gouvernementales

La [FAQ DINUM Cloud au centre](https://www.numerique.gouv.fr/offre-accompagnement/cloud-administrations/faq/) distingue son périmètre obligatoire et les collectivités. On ne peut pas en tirer une obligation universelle SecNumCloud pour tous les courriels de toutes les communes.

Pour rechercher le niveau de souveraineté et de sécurité adapté, contrôler l'offre exacte dans le [catalogue officiel ANSSI](https://messervices.cyber.gouv.fr/visas/catalogue-produits-services-profils-de-protection-sites-certifies-qualifies-agrees-anssi.pdf), sa décision et son périmètre au jour de l'achat. « OVH » ne désigne pas un périmètre de qualification unique. Une infrastructure qualifiée ne qualifie pas automatiquement l'application qu'on y installe, comme le précise la [FAQ ANSSI](https://cyber.gouv.fr/enjeux-technologiques/cloud/faq-qualification-secnumcloud/). Vérifier séparément calcul GPU, endpoint IA, sauvegardes et accès d'administration.

Le caractère français de Mistral ne garantit pas à lui seul l'absence de transfert ou de conservation pour chaque fonctionnalité/API. Choisir entre modèle auto-hébergé sur un périmètre qualifié ou service d'inférence contractuellement validé ; ne pas activer de fournisseurs externes dans AppFlowy par défaut.

Les [recommandations ANSSI pour les systèmes d'IA générative](https://messervices.cyber.gouv.fr/documents-guides/Recommandations_de_s%C3%A9curit%C3%A9_pour_un_syst%C3%A8me_d_IA_g%C3%A9n%C3%A9rative.pdf) motivent les frontières techniques retenues : mails non fiables, modèle sans outils d'action, sortie structurée validée et décision humaine traçable.

## Ancien circuit Gmail / ChatGPT / Notion

Faire l'inventaire des copies et accès avec le DPO et l'archiviste. Ne pas effectuer une suppression massive avant de connaître les obligations de conservation et la réponse appropriée à la situation. L'éventuelle qualification d'incident et les obligations d'information/notification nécessitent une évaluation des faits ; elles ne sont pas déduites automatiquement de cette conversation.

Cette note est une préparation technique fondée sur les sources officielles consultées le 14 novembre 2026. Une validation institutionnelle et une vérification des textes/contrats courants restent nécessaires avant ouverture du pilote.
