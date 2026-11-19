import assert from 'node:assert/strict';
import test from 'node:test';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
import {resolveWorkProfile} from './work-profile-model.mjs';

const bundled=await build({entryPoints:[fileURLToPath(new URL('./data.ts',import.meta.url))],bundle:true,platform:'node',format:'esm',write:false,logLevel:'silent'});
const {loadWorkspace}=await import('data:text/javascript;base64,'+Buffer.from(bundled.outputFiles[0].text).toString('base64'));
const session={authenticated:true,account:{id:'a'},actor:{tenant_id:'tenant',actor_id:'actor'}};
function fixture(commissions,rows=[]){
 const calls=[];
 const bootstrap={commissions,permissions:Object.fromEntries(['mail','organization','members','audit'].map(key=>[key,{read:false,write:false}]))};
 const client={session:async()=>session,bootstrap:async()=>{calls.push('bootstrap');return bootstrap;},projects:async filter=>{calls.push(filter);return {items:rows};},summaries:async()=>({items:[]}),project:async id=>({project:rows.find(item=>item.id===id),facts:[],events:[],notes:[]}),documents:async()=>({items:[]})};
 return {client,calls,bootstrap};
}

test('a fresh bootstrap validates the commission filter before a dossier request starts',async()=>{
 const {client,calls}=fixture([{id:'commission-3',can_read:true}]);
 await loadWorkspace(client,'commission-3');
 assert.deepEqual(calls,['bootstrap',{commission_id:'commission-3'}]);
});

test('a removed commission falls back to server-authorized dossiers, including direct grants',async()=>{
 const {client,calls}=fixture([{id:'commission-4',can_read:false}],[{id:'shared-dossier',name:'Dossier partagé',commission_id:'commission-4'}]);
 const data=await loadWorkspace(client,'commission-4');
 assert.deepEqual(calls,['bootstrap',{}]);
 assert.equal(data.state.projects[0].id,'shared-dossier');
 assert.deepEqual(resolveWorkProfile(data.session,data.bootstrap,'commission-4',data.state.projects.length>0),{status:'ready',commissionId:'all',changed:true});
});

test('organization onboarding remains ahead of profile bootstrap and business requests',async()=>{
 const {client,calls}=fixture([{id:'commission-3',can_read:true}]);
 client.session=async()=>({...session,organization_required:true});
 const data=await loadWorkspace(client,'commission-3');
 assert.deepEqual(calls,[]);assert.equal(data.bootstrap,null);assert.deepEqual(data.state.projects,[]);
});
