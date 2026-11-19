# Audit des solutions et de l'application actuelle

**Date : 16 novembre 2026. Statut : recommandations proposées, aucune migration engagée.**

Compléments expérimentaux réalisés après cet audit initial : [essai réel OpenProject](../../travaux-openproject-evaluation/README.md), puis [code récupéré et comparaison des briques](../../travaux-oss-comparison-2026-11-16/README.md). Le périmètre décrit ci-dessous est celui de l'audit documentaire initial ; les installations, tests effectivement exécutés et workflows non exécutés sont distingués dans ces nouveaux rapports.

Périmètre : chantiers municipaux, mails Exchange externes, planning/Gantt, documents, assistant Mistral, droits et hébergement maîtrisé. L'audit confronte le code local 0.8.1 et ses manifestes aux documentations et licences officielles des candidats. Il ne comprend ni installation comparative de ces produits, ni benchmark de performance, ni test d'intrusion. Les éditions et offres doivent être revérifiées au moment d'un achat.

## Résultat de l'audit

**OpenProject est le premier socle complet à évaluer si l'objectif est de réduire le développement des fonctions standard de gestion de projet. Zammad est le candidat le plus pertinent pour une vraie boîte de traitement des demandes avec IA. Aucun des deux n'est aujourd'hui le backend de Travaux.**

L'application actuelle assemble une interface issue de Lovable, le moteur documentaire AFFiNE/BlockSuite et un backend métier Python propre au projet. Ce n'est ni un Notion auto-hébergé, ni un serveur AFFiNE complet, ni un ERP libre installé derrière une nouvelle façade.

La recommandation antérieure « reprendre leurs briques » demandait une précision : OpenProject et Zammad sont principalement des applications complètes, pas des bibliothèques Python interchangeables. Les voies réalistes sont adopter le produit, l'intégrer par API, ou réutiliser des bibliothèques protocolaires indépendantes. Copier une partie d'un produit exige de conserver sa licence et d'examiner les obligations applicables ; une API ne résout pas à elle seule toutes les questions de licence ou de droits.

## Ce qui était utilisé jusque-là

### Référence métier et historique

Les photos fournies montrent une base **Notion** « Suivi des travaux », avec dates, demandeurs, entreprises, lieux, statuts, priorités, observations, coûts, notes, pièces, responsables et échéances. Elles établissent le format métier de référence, pas l'existence d'un import automatique de la messagerie.

Une ancienne rubrique du dossier évoque « Gmail / ChatGPT / Notion ». Elle ne contient ni chronologie vérifiable ni preuve d'une connexion effective entre ces services. L'audit ne peut donc pas affirmer que la boîte Exchange transitait déjà automatiquement par Gmail ou ChatGPT. Le site actuel conserve ses données dans sa propre base, pas dans Notion.

### Composition vérifiée de Travaux 0.8.1

| Partie visible | Technologie réellement présente | Ce que cela apporte et sa limite |
| --- | --- | --- |
| Interface agréable, navigation et écrans | Code React 19 / TypeScript / Tailwind issu des archives Lovable et adapté au backend | Lovable a fourni la base d'interface ; aucun service Lovable ou Supabase n'est nécessaire dans le chemin d'exécution actuel. Les données fictives du prototype ont été raccordées/remplacées par nos API. |
| Pages et tableaux de chantier | **AFFiNE/BlockSuite 0.22.4 + Yjs 13.6.33** embarqués | Vrai éditeur de blocs et base native, avec état sauvegardé. Le serveur AFFiNE complet, ses comptes et toutes ses fonctions ne sont pas installés. La présence de Yjs n'implique pas que la collaboration temps réel soit livrée. |
| Planning/Gantt | **Frappe Gantt 1.2.2** et adaptations métier | Bibliothèque de visualisation réellement intégrée ; **ERPNext/Frappe ERP n'est pas installé**. Le calcul des données, la sauvegarde et les règles métier restent à notre charge. |
| Agenda | **FullCalendar 6.1.21**, adaptateurs ICS/CalDAV | Calendrier existant réutilisé. OAuth Google/Microsoft ne doit pas être déduit de la présence d'un calendrier. |
| Données, API et règles métier | **Python/FastAPI, SQLite**, code `travaux` | Stockage des chantiers, sources, propositions, décisions, actions, conversations et historique. Cette couche métier est spécifique au projet. |
| Droits et sessions | **Casbin**, cryptographie et sessions locales | Moteur de règles réutilisé, mais identité protégée encore partagée et droits surtout par espace. Ce n'est pas un IAM institutionnel complet. |
| Lecture de mails | **exchangelib / EWS** | Un adaptateur Exchange réel existe dans le code ; la recette du parcours privé utilise un lecteur fictif. Aucun Exchange municipal n'est connecté à la démo. Graph et IMAP/OAuth mail ne sont pas implémentés. |
| PDF/DOCX et mail original | **pypdf, python-docx**, parseurs mail et code d'import | Extraction et conservation des originaux/PJ déjà prévues, avec limites. La quarantaine actuelle n'est pas une sandbox antivirus complète. |
| Recherche de l'assistant | **SQLite FTS5 / BM25** et orchestration propre au projet | Recherche lexicale de passages ; pas de plateforme RAGFlow, Dify, Haystack ou base vectorielle complète installée. |
| Réponse et popup de chat | UI de conversation, historique local et sélecteur Mistral optionnel | En démo, réponses locales sans appel LLM. L'adaptateur Mistral sélectionne des passages exacts ; une conversation générative libre et évaluée reste à développer. La bulle ne prouve pas une connexion à ChatGPT ou Mistral. |
| Adresses de destinataires | Copie du parseur **Nodemailer**, MIT-0 | Analyse des adresses seulement ; pas de serveur ni transport SMTP Nodemailer complet ajouté. |
| Notifications Telegram | Adaptateur Bot API spécifique, désactivé dans la démo | Code présent et tests simulés ; aucun bot réel n'est nécessaire à la version publique. |

Preuves principales : [manifest Python](../pyproject.toml), [manifest du frontend](../frontend-lovable/package.json), [manifest de l'éditeur](../native-editor/package.json), [Planning.tsx](../frontend-lovable/src/features/workspace/Planning.tsx), [Agenda.tsx](../frontend-lovable/src/features/workspace/Agenda.tsx), [recherche](../src/travaux/retrieval.py), [assistant](../src/travaux/assistant_dossier.py), [conversations](conversation-integration-2026/README.md), [réemploi du code](REUTILISATION_CODE.md).

### Ce qui a été repris partiellement ou seulement étudié

- **La Suite Docs** : feuille de style réellement utilisée pour l'export HTML ; pas son serveur de documents complet.
- **Grist** : deux fonctions d'URL conservées et importées ; aucun moteur Grist installé. Aucun appel courant à leur wrapper `safeUrl()` n'a été établi par la recherche statique de cet audit.
- **OpenGateLLM** : patron de construction Docker adapté ; pas sa gateway de modèles ni son système de gouvernance complet.
- **AppFlowy** : adaptateurs/documents historiques, remplacés dans l'UX actuelle par l'éditeur embarqué. Ils ne prouvent pas qu'un serveur AppFlowy soit exploité sur le site actuel.
- **Haystack, RAGFlow, OpenProject, Zammad, Nextcloud Mail, Casdoor, Frappe/Odoo** : études et lectures de code ne valent pas installation. Certaines idées ont guidé le raccord métier ; cela ne transforme pas ces produits en composants du runtime.

Le bénéfice du choix actuel est une UX spécifique et un circuit de preuves cohérent. Sa contrepartie est réelle : les connecteurs, les règles métier, les migrations, les droits fins, la recherche et l'exploitation sont davantage à maintenir par notre projet.

## Critères de comparaison

Les candidats ont été évalués sur cinq questions, sans score chiffré artificiel :

1. Couvre-t-il les fonctions standard de chantier : actions, responsables, dates, dépendances, Gantt et documents ?
2. Comment lit-il Exchange et que modifie-t-il dans la boîte ?
3. L'IA, le SSO et les droits nécessaires existent-ils dans l'édition libre examinée ?
4. Peut-on conserver les sources, leurs permissions et une validation humaine ?
5. Quelle infrastructure et quelle reprise des données impose-t-il ?

Le support d'un protocole, une licence libre ou une fonctionnalité de sécurité ne constituent pas une certification de la configuration finale.

## Les meilleurs socles projet selon le besoin

| Solution | Apport concret | Édition libre et frontières | Verdict pour Travaux |
| --- | --- | --- | --- |
| **OpenProject** | Projets, tâches/work packages, dépendances, Gantt, wiki, PJ et rôles projet ; import de mails vers tâches/commentaires. | GPLv3. Le Gantt est dans Community. OIDC/SAML, MCP IA et plusieurs fonctions avancées sont Enterprise. TOTP/WebAuthn sont documentés séparément du SSO. | **Premier candidat pour un socle projet maintenu.** Adoption de son UX = moins de fonctions standard à développer. Conserver toute notre UX devant ses API = intégration conséquente. Notre revue des propositions IA reste à raccorder. |
| **ERPNext / Frappe** | Projets/tâches/Gantt, comptes mail et communications, Issue liée au projet, achats/fournisseurs/dépenses. | ERPNext GPLv3, framework Frappe MIT. Le circuit documentaire IA spécifique reste à intégrer. | **Meilleur candidat si achats et finances entrent dans le périmètre.** Trop de configuration ERP si le besoin demeure un suivi de chantier simple. |
| **Odoo Community** | Projets/tâches, mail alias vers tâche, échanges/PJ ; modules OAuth et TOTP publics. | Community LGPLv3. Gantt officiel, Documents et couches IA de l'offre complète ne doivent pas être supposés inclus dans Community ; alternatives tierces à qualifier. | Pertinent si la collectivité utilise déjà Odoo. Moins direct ici pour un Gantt libre avec notre gestion des preuves. |
| **Plane Community** | UX de projets/work items, Gantt et pages. | Community AGPLv3 et Commercial distincts ; Intake Email/Forms et SSO Business, fonctions IA et gouvernance avancée selon offres payantes. | Candidat UX moderne, mais les fonctions décisives mail/identité/IA conduisent au-delà du seul cœur libre. |

Sources : [OpenProject Community](https://www.openproject.org/community-edition/), [authentification](https://www.openproject.org/docs/system-admin-guide/authentication/), [MFA](https://www.openproject.org/docs/system-admin-guide/authentication/two-factor-authentication/), [mail entrant](https://www.openproject.org/docs/installation-and-operations/configuration/incoming-emails/), [MCP/Enterprise](https://www.openproject.org/blog/openproject-17-8-release/) ; [ERPNext vues projet](https://docs.frappe.io/erpnext/user/manual/en/project-views), [mail](https://docs.frappe.io/erpnext/email-account), [licences](https://docs.frappe.io/legal/others/license-and-trademark) ; [Odoo licence](https://github.com/odoo/odoo/blob/20.0/LICENSE), [email vers tâche](https://www.odoo.com/documentation/20.0/applications/services/project/tasks/email_alias.html), [Gantt Enterprise](https://www.odoo.com/documentation/20.0/de/developer/tutorials/backend.html) ; [éditions Plane](https://developers.plane.so/self-hosting/editions-and-versions), [offres](https://plane.so/pricing).

## Messagerie et IA : deux candidats, deux usages

**Zammad est le meilleur candidat étudié pour gérer une boîte dédiée de demandes**, avec tickets, groupes, historique, Microsoft 365 Graph et résumés/classification IA utilisant notamment Mistral ou Ollama. Licence AGPLv3. Il ne remplace pas le Gantt ou le domaine des chantiers. [Canaux mail](https://admin-docs.zammad.org/en/latest/channels/email/index.html), [fournisseurs IA](https://admin-docs.zammad.org/en/latest/ai/provider.html), [licence](https://github.com/zammad/zammad/blob/develop/LICENSE).

**Limite déterminante : son import mail générique n'est pas une lecture passive de ta boîte personnelle.** La documentation indique suppression des messages importés par défaut ; avec conservation activée, marquage comme lus et import des seuls non lus, pouvant manquer des messages lus ailleurs. Des réponses automatiques peuvent aussi partir selon la configuration et le mode d'archivage. Ces effets doivent être acceptés, configurés et testés sur une boîte dédiée ; les paramètres documentés ne garantissent pas une lecture strictement passive. Ne pas brancher directement un historique municipal en supposant « lecture seule ». [Paramètres et avertissements officiels](https://admin-docs.zammad.org/en/latest/channels/email/accounts/account-setup.html).

Le canal Graph demande notamment `Mail.ReadWrite` et `Mail.Send`, avec variantes pour boîtes partagées : ce ne sont pas des permissions strictement de lecture. Son comportement doit être testé séparément du canal générique. L'intégration Zammad appelée « Exchange » concerne les contacts, pas un collecteur mail EWS. [Permissions Graph](https://admin-docs.zammad.org/en/latest/channels/microsoft365-graph/accounts.html), [intégration Exchange](https://admin-docs.zammad.org/en/latest/system/integrations/exchange.html).

**Nextcloud Mail + Assistant est pertinent si la collectivité utilise déjà Nextcloud** : mails IMAP/SMTP, fichiers et assistant avec fournisseurs externes ou locaux. Ce n'est pas à lui seul un outil de gestion de projets complet. Vérifier le support XOAUTH2 côté Microsoft, sans confondre IMAP et Graph. Les licences et versions des apps doivent être relevées séparément. [Mail](https://docs.nextcloud.com/server/stable/admin_manual/groupware/mail.html), [Assistant](https://docs.nextcloud.com/server/stable/admin_manual/ai/index.html).

Limite concrète : Context Chat documente la non-application des règles de l'app `files_accesscontrol`. Un utilisateur voyant le document dans Files peut encore en retrouver le contenu par chat malgré un refus de cette app. Cela ne signifie pas que toute permission Nextcloud est ignorée, mais interdit de promettre une reprise universelle des règles d'accès. [Limitation Context Chat](https://docs.nextcloud.com/server/stable/admin_manual/ai/app_context_chat.html#file-access-control-rules-not-supported).

**Chatwoot** répond surtout au support omnicanal. Son cœur Community MIT ne doit pas être confondu avec Captain IA et les fonctions de gouvernance commerciales. Il ne ressort pas devant Zammad pour notre besoin mail/ticket auto-hébergé avec Mistral. À reconsidérer si chat public et canaux sociaux deviennent centraux. [Offres auto-hébergées](https://www.chatwoot.com/pricing/self-hosted-plans), [Captain](https://www.chatwoot.com/hc/user-guide/articles/1755284287-how-to-enable-captain-on-self_hosted-installations).

**Frappe Helpdesk**, AGPLv3, devient pertinent si ERPNext est choisi : mail vers ticket, équipes et routage. L'intégration officielle ERPNext documente notamment les clients ; elle ne démontre pas notre circuit ticket vers chantier. Aucun Mistral natif prêt à l'emploi dans Helpdesk n'a été établi par les sources consultées. [Projet](https://github.com/frappe/helpdesk), [Outlook OAuth/IMAP](https://docs.frappe.io/helpdesk/faq/setting-up-outlook-for-frappe).

**EmailEngine** est une alternative technique particulièrement proche du besoin de connecteur derrière notre UX : API unifiée IMAP/SMTP, Gmail et Graph, synchronisation et webhooks. Son intérêt est de réduire la maintenance protocolaire ; nos droits et règles métier restent à réaliser. Il est toutefois **source-available avec licence commerciale**, pas un logiciel libre gratuit : abonnement après essai. [Statut et licence officiels](https://github.com/postalsys/emailengine).

Pour garder notre application, la voie la plus ciblée reste un connecteur **Graph pour Exchange Online**, ou un protocole autorisé par la DSI pour Exchange Server. Une bibliothèque IMAP comme IMAPClient sert aux serveurs qui le permettent ; elle n'apporte ni le consentement OAuth complet ni les droits métier. [IMAPClient](https://github.com/mjs/imapclient), [retrait EWS Online](https://learn.microsoft.com/en-gb/exchange/clients-and-mobile-in-exchange-online/deprecation-of-ews-exchange-online).

## Recherche documentaire et assistant : quelle brique ajouter

| Candidat | Intérêt | Réserve et recommandation |
| --- | --- | --- |
| **Haystack** — Apache-2.0 | Framework Python de pipelines documentaires, recherche et génération ; intégration Mistral et endpoint configurable. | **Premier candidat de bibliothèque si notre moteur doit évoluer**, car il peut s'intégrer au backend existant. Il n'apporte pas automatiquement notre IAM, nos permissions, la qualité des citations ou la validation métier. Son adoption doit répondre à un besoin mesuré, pas remplacer BM25 par principe. [Mistral](https://docs.haystack.deepset.ai/docs/mistralchatgenerator), [API configurable](https://docs.haystack.deepset.ai/reference/integrations-mistral), [licence](https://github.com/deepset-ai/haystack/blob/main/LICENSE). |
| **RAGFlow** — Apache-2.0 | Plateforme documentaire/RAG avec analyse de documents complexes et citations. | **Premier candidat de plateforme si les PDF/tableaux deviennent le problème central.** Introduit une seconde chaîne d'indexation, des permissions à raccorder et davantage de services. Le démarrage recommandé est 4 CPU, 16 Go RAM et 50 Go disque, hors dimensionnement du modèle. [Documentation](https://ragflow.io/docs), [licence](https://github.com/infiniflow/ragflow/blob/main/LICENSE). |
| **Dify** | Construction visuelle de workflows, RAG et applications IA. | Licence Apache modifiée avec conditions sur multi-tenant/workspaces et marque. Utile pour prototyper un workflow ; pas un choix de SaaS multi-collectivités supposé libre sans restriction. [Licence réelle](https://github.com/langgenius/dify/blob/main/LICENSE). |
| **Open WebUI** | Interface IA complète, RAG, groupes et fonctions d'accès. | Utile pour un chat interne autonome ; ajouterait une autre UX et un autre stockage à notre popup. Licence actuelle avec condition de marque, pas simple BSD-3 sans restriction. [Fonctions](https://docs.openwebui.com/features/), [licence](https://docs.openwebui.com/license/). |
| **Onyx** | Recherche transverse, connecteurs et chat avec sources ; cœur Community MIT. | L'édition Enterprise apporte notamment SSO, synchronisation des permissions et contrôles de groupes. Bon candidat de recherche d'organisation si ce budget est assumé ; ne pas assimiler Community aux garanties Enterprise. [Éditions](https://docs.onyx.app/welcome), [licence](https://github.com/onyx-dot-app/onyx/blob/main/LICENSE). |

La recherche lexicale actuelle reste un choix valable à petite échelle. L'amélioration doit être jugée sur les mêmes questions françaises, sources et habilitations : meilleure réponse, meilleure preuve, absence de fuite, délais et coût. Un moteur vectoriel ne résout pas à lui seul les homonymes, les dates contradictoires ou le choix d'un responsable.

## Décision proposée et conséquences

**Pour un logiciel spécifique aux élus et services, conserver l'UX actuelle et ses moteurs embarqués reste cohérent. Pour minimiser durablement les fonctions de projet développées sur mesure, OpenProject mérite une comparaison concrète avant de poursuivre leur extension.** Le code déjà écrit ne suffit pas à justifier le maintien de toute l'architecture.

Découpage proposé :

1. Garder BlockSuite/Yjs, Frappe Gantt et FullCalendar tant qu'ils répondent à la recette ; ce sont déjà de vrais réemplois.
2. Ne pas installer simultanément OpenProject, ERPNext et Zammad. Choisir une autorité unique pour chantiers/actions ; éviter deux statuts ou deux responsables divergents.
3. Évaluer OpenProject comme **alternative au socle projet**, avec un chantier représentatif, deux acteurs aux droits différents, documents, dépendances et export. Si son UX suffit, adopter le produit standard apporte un gain de maintenance. Si toute l'UX doit être réécrite devant ses API, chiffrer ce travail avant d'en attendre ce gain.
4. Garder une collecte mail passive spécifique si l'objectif est de lire une boîte existante sans la modifier. Retenir Zammad si l'organisation veut plutôt une boîte dédiée de demandes, des tickets, des réponses et leur suivi.
5. Préférer une bibliothèque Haystack si le besoin prouvé est une orchestration RAG plus riche. Retenir RAGFlow seulement si ses gains documentaires justifient un service séparé. Dans les deux cas, conserver la décision et le filtrage des droits côté serveur.

Une migration reprendrait plus qu'un tableau CSV : documents Yjs, mails/PJ originaux, versions, citations, liens de chantier, propositions rejetées/acceptées, identités et historique. Les coûts de licence, d'infrastructure et d'intégration doivent être chiffrés sur l'édition retenue ; aucun délai ou prix de migration n'a été inventé dans cet audit.

Les écarts de sécurité observés précédemment demeurent prioritaires quel que soit le produit : identité individuelle/MFA, droits par chantier avant l'IA, coffre/rotation, isolation des pièces, conservation et restauration hors site. Lire le [dossier Exchange/OVH/Mistral](cible-ovh-exchange-mistral-2026-11-16.md). Aucune solution libre ne rend automatiquement le déploiement conforme au RGPD ou qualifié SecNumCloud.
