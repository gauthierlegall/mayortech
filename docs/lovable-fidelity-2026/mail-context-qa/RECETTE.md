# Recette locale — Échanges, brouillons et actions

Vérification du 15 novembre 2026 sur le client compilé servi en même origine à `http://127.0.0.1:8766/`, Chrome headless isolé. Données entièrement fictives. Aucun envoi de courriel, appel IA ou action sur le site public.

**Résultat : 7 parcours réussis, aucune erreur JavaScript ni réponse HTTP en erreur.** Les observations et le nettoyage sont consignés dans [checks.json](checks.json). Script reproductible : `work/qa_mail_context_actions.py` ; nettoyage ciblé : `work/cleanup_mail_qa_action.py`.

1. À 1920 × 1080 et 390 × 844, cliquer une conversation conserve le chantier et `view=exchanges&mail=…`. Recharger rouvre la même conversation. Le retour mobile retrouve la liste du chantier.
2. Répondre ouvre un véritable formulaire. Une saisie suivie immédiatement de Fermer conserve le brouillon dans la file partagée ; la navigation demeure dans le chantier.
3. Ce brouillon apparaît dans le dossier global Brouillons, issu de la même clé locale `travaux:mail-drafts:v1`.
4. À tous, Transférer et Préparer une réponse ouvrent des brouillons reliés au message original. Aucun destinataire absent n’est inventé. À tous affiche dans le dialogue un avertissement lorsque les destinataires d’origine manquent. Le modèle de réponse est explicitement présenté comme un texte à compléter, sans envoi.
5. Créer une action écrit dans la base native du chantier. Après rechargement, sa fiche expose Message lié et ouvre exactement le courriel choisi. Le titre, le responsable et l’échéance restent sous contrôle humain ; aucune décision sur les faits du dossier n’est prise.
6. Le dialogue Répondre reste utilisable à 390 px, sans débordement horizontal de la page, puis revient au contexte du chantier.
7. La seule action créée pour cette recette a été retirée par son identifiant, avec `store.deleteBlock(model)` puis sauvegarde CAS. Les trois lignes antérieures sont strictement identiques avant et après. Identifiant retiré et preuve de comparaison : champ `cleanup` du rapport JSON. Aucun reset ni réensemencement.

## Captures observées

Les captures ci-dessous proviennent du navigateur local réel ; les animations sont terminées pour rendre les dialogues lisibles.

- [Message dans le chantier, 1920 px](1920-context-message.png)
- [Message dans le chantier, 390 px](390-context-message.png)
- [À tous : destinataires connus et avertissement](1920-reply-all.png)
- [Transférer : destinataire à renseigner](1920-forward.png)
- [Modèle de réponse clairement indiqué](1920-template.png)
- [Action enregistrée et lien vers le message](1920-created-action-proof.png)
- [Brouillon sur mobile](390-reply.png)

## Portée et limites

La recette navigateur concerne le pilote local en mode démonstration : les brouillons restent sur l’appareil. Le chemin privé exige les capacités serveur `server_drafts` et `can_compose` ; il n’a pas été présenté comme connecté à Exchange. Les tests du composant de sauvegarde couvrent la file et les erreurs, mais cette recette n’est pas une validation d’un serveur Exchange réel. Les destinataires To/Cc absents du corpus ne peuvent pas être reconstitués. Aucun SMTP, message Envoyé simulé ou génération LLM n’a été ajouté.
