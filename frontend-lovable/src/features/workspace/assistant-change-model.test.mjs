import test from 'node:test';
import assert from 'node:assert/strict';
import {canRequestChange,messageAttempt,assistantProposal,proposalPresentation} from './assistant-change-model.mjs';
const hash='a'.repeat(64);
const raw={id:'change-1',conversation_id:'c1',project_id:'p1',plan:{operation:'property',field:'status',value:'Terminé'},plan_hash:hash,status:'pending',result:{},expires_at:2_000_000_000};
test('mutation mode requires explicit write capability and a specific dossier',()=>{
 assert.equal(canRequestChange({permissions:{workspace:{write:true}}},'p1'),true);
 assert.equal(canRequestChange({permissions:{workspace:{write:true}}},''),false);
 assert.equal(canRequestChange({permissions:{workspace:{read:true}}},'p1'),false);
});
test('ambiguous send retries keep one key only for identical thread, content and intent',()=>{
 const first=messageAttempt(null,{threadId:'c',content:' État ? ',intent:'question'},()=> 'first');
 assert.equal(first.content,'État ?');
 assert.equal(messageAttempt(first,{threadId:'c',content:'État ?',intent:'question'},()=> 'second').clientId,'first');
 assert.equal(messageAttempt(first,{threadId:'c',content:'État ?',intent:'change'},()=> 'second').clientId,'second');
 assert.equal(messageAttempt(first,{threadId:'other',content:'État ?',intent:'question'},()=> 'third').clientId,'third');
 assert.throws(()=>messageAttempt(null,{threadId:'c',content:' ',intent:'change'},()=> 'id'));
 assert.throws(()=>messageAttempt(null,{threadId:'c',content:'abc',intent:'automatic'},()=> 'id'));
});
test('proposal is bound to the message, conversation and selected dossier',()=>{
 assert.equal(assistantProposal(raw,{id:'change-1',conversationId:'c1',projectId:'p1'}).plan.value,'Terminé');
 for(const change of [{id:'other'},{project_id:'other'},{conversation_id:'other'},{plan_hash:'short'},{plan_hash:'z'.repeat(64)},{status:'unknown'},{plan:{operation:'permission',field:'role',value:'admin'}},{plan:{operation:'property',field:'role',value:'admin'}}]) assert.throws(()=>assistantProposal({...raw,...change},{id:'change-1',conversationId:'c1',projectId:'p1'}));
});
test('proposal presentation shows the exact value, operation and controlled property label',()=>{
 assert.deepEqual(proposalPresentation(assistantProposal(raw,{id:'change-1',conversationId:'c1',projectId:'p1'})),{label:'Statut',value:'Terminé'});
 assert.deepEqual(proposalPresentation({...raw,plan:{operation:'action',field:'',value:'Vérifier les accès'}}),{label:'Créer une action',value:'Vérifier les accès'});
 assert.deepEqual(proposalPresentation({...raw,plan:{operation:'note',field:'',value:'À relire'}}),{label:'Ajouter une note',value:'À relire'});
});
