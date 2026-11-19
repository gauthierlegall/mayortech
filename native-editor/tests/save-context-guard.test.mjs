import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

// Execute the production save closure with its actual async boundary. The SDK's
// document renderer is irrelevant to the credential switch being reproduced.
const source=await readFile(new URL('../src/editor.ts',import.meta.url),'utf8');
const start=source.indexOf('  const save = () => {');
const end=source.indexOf('\n  const addBlock =',start);
assert.ok(start>=0&&end>start);
const saveClosure=source.slice(start,end);
function savingWith(environment){
 return Function('environment',`const {options,getState,getText,fetch,endpoint,encodeState,EDITOR_VERSION}=environment;let disposed=false,saving=null,generation=0,revisionHash=null,dirty=true;${saveClosure};return save;`)(environment);
}

test('a context revoked during asynchronous text export prevents the native PUT',async()=>{
 let active=true,release;const events=[];
 const save=savingWith({options:{beforeSave:()=>{events.push('guard');if(!active)throw Error('context_changed');}},getState:()=>new Uint8Array([1]),getText:()=>new Promise(resolve=>{release=()=>resolve('Texte humain fictif');}),fetch:async()=>{events.push('PUT');return{ok:true,json:async()=>({revision_hash:'a'.repeat(64)})};},endpoint:'/api/v1/pages/page/state',encodeState:()=> 'AQ==',EDITOR_VERSION:'blocksuite-0.22.4'});
 const pending=save();active=false;release();
 await assert.rejects(pending,/context_changed/);
 assert.deepEqual(events,['guard']);
});

test('native save checks its context after export and preserves the ordinary CAS payload',async()=>{
 const events=[];let body;
 const save=savingWith({options:{beforeSave:()=>events.push('guard')},getState:()=>new Uint8Array([1]),getText:async()=>{events.push('export');return'Texte fictif';},fetch:async(endpoint,options)=>{events.push('PUT');body=JSON.parse(options.body);return{ok:true,json:async()=>({revision_hash:'a'.repeat(64)})};},endpoint:'/api/v1/pages/page/state',encodeState:()=> 'AQ==',EDITOR_VERSION:'blocksuite-0.22.4'});
 await save();
 assert.deepEqual(events,['export','guard','PUT']);
 assert.deepEqual(body,{state_base64:'AQ==',expected_revision_hash:null,text:'Texte fictif',editor_version:'blocksuite-0.22.4'});
});
