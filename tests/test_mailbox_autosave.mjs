import test from 'node:test';
import assert from 'node:assert/strict';
import {draftPayload,createDraftSaveQueue} from '../web/mailbox.js';

const initial=()=>({id:'local-550e8400-e29b-41d4-a716-446655440000',to:'Alice <alice@example.invalid>',cc:'',bcc:'',subject:'Visite fictive',body:'Version 1'});
const deferred=()=>{let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};};
function setup(api){let draft=initial(),dirty=true;const queue=createDraftSaveQueue({api,getDraft:()=>draft,isDirty:()=>dirty,markClean:()=>{dirty=false;}});return {queue,get draft(){return draft;},get dirty(){return dirty;},edit(body){draft.body=body;dirty=true;}};}

test('draft payload only includes editable fields, never actor identity or server metadata',()=>{
  const value=draftPayload({...initial(),created_at:'server-time',updated_at:'later',revision:7,client_id:'readonly',actor_id:'untrusted',tenant_id:'untrusted'});
  assert.deepEqual(Object.keys(value).sort(),['bcc','body','cc','in_reply_to','mode','subject','to']);
  assert.deepEqual(value.to,['alice@example.invalid']);
});

test('flush waits for typing that occurs while the first create is in flight',async()=>{
  const first=deferred(),calls=[];
  const state=setup({createMailDraft:async payload=>{calls.push(['create',payload]);return first.promise;},saveMailDraft:async(id,payload)=>{calls.push(['patch',id,payload]);return {id,revision:2};}});
  const saving=state.queue.flush();
  state.edit('Version 2 pendant la sauvegarde');
  assert.equal(state.queue.flush(),saving);
  first.resolve({id:'server-id',revision:1});
  await saving;
  assert.equal(calls.length,2);
  assert.equal(calls[0][1].client_id,'550e8400-e29b-41d4-a716-446655440000');
  assert.equal(calls[1][0],'patch');
  assert.equal(calls[1][2].body,'Version 2 pendant la sauvegarde');
  assert.equal(calls[1][2].expected_revision,1);
  assert.equal(state.dirty,false);
});

test('ambiguous create retries the original idempotent payload before patching newer text',async()=>{
  let count=0;const calls=[];
  const state=setup({createMailDraft:async payload=>{calls.push(structuredClone(payload));if(++count===1)throw Error('response lost');return {id:'same-server-id',revision:1};},saveMailDraft:async(id,payload)=>{calls.push({id,...payload});return {id,revision:2};}});
  await assert.rejects(state.queue.flush(),/response lost/);
  assert.equal(state.dirty,true);
  state.edit('Version après erreur réseau');
  await state.queue.flush();
  assert.deepEqual(calls[0],calls[1]);
  assert.equal(calls[2].body,'Version après erreur réseau');
  assert.equal(calls[2].expected_revision,1);
  assert.equal(state.dirty,false);
});

test('conflict preserves the local draft and its expected server revision',async()=>{
  const state=setup({createMailDraft:async()=>({id:'server-id',revision:1}),saveMailDraft:async()=>{throw Error('stale_draft');}});
  await state.queue.flush();state.edit('Texte local à conserver');
  await assert.rejects(state.queue.flush(),/stale_draft/);
  assert.equal(state.dirty,true);
  assert.equal(state.draft.body,'Texte local à conserver');
  assert.equal(state.draft.revision,1);
});

test('browser-only drafts never call a server API',async()=>{
  let local,dirty=true;const draft=initial();
  const queue=createDraftSaveQueue({api:{createMailDraft:()=>{throw Error('must not contact server');}},getDraft:()=>draft,isDirty:()=>dirty,markClean:()=>{dirty=false;},isServer:()=>false,saveLocal:value=>{local=structuredClone(value);}});
  await queue.flush();assert.equal(local.body,draft.body);assert.equal(dirty,false);
});

test('a replay that finds a newer human edit never silently overwrites that revision',async()=>{
  let calls=0;
  const state=setup({createMailDraft:async()=>{if(++calls===1)throw Error('response lost');return {id:'server-id',revision:2};},saveMailDraft:async()=>{throw Error('must not overwrite');}});
  await assert.rejects(state.queue.flush(),/response lost/);
  state.edit('Texte local à conserver');
  await assert.rejects(state.queue.flush(),/autre onglet/);
  assert.equal(state.dirty,true);
  assert.equal(state.draft.body,'Texte local à conserver');
  assert.ok(state.draft.id.startsWith('local-'));
});
