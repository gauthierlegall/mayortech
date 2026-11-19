import assert from 'node:assert/strict';
import test from 'node:test';
import {nativePageMayHaveActions,nativeReadPlan} from './native-read-plan.mjs';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
import {api} from '../../../../web/api.js';

// Synthetic Y.Doc blocks encoded with native-editor's Y.encodeStateAsUpdate V1.
const noteState='AQQqACcBBmJsb2NrcwRwYWdlASgAKgAHZmxhdm91cgF3C2FmZmluZTpwYWdlJwEGYmxvY2tzBG5vdGUBKAAqAgdmbGF2b3VyAXcLYWZmaW5lOm5vdGUA';
const databaseState='AQYqACcBBmJsb2NrcwRwYWdlASgAKgAHZmxhdm91cgF3C2FmZmluZTpwYWdlJwEGYmxvY2tzBG5vdGUBKAAqAgdmbGF2b3VyAXcLYWZmaW5lOm5vdGUnAQZibG9ja3MCZGIBKAAqBAdmbGF2b3VyAXcPYWZmaW5lOmRhdGFiYXNlAA==';

test('the known Yjs V1 note state skips action mounting while real database markers remain',()=>{
 assert.equal(nativePageMayHaveActions({state_base64:noteState,editor_version:'blocksuite-0.22.4'}),false);
 assert.equal(nativePageMayHaveActions({state_base64:databaseState,editor_version:'blocksuite-0.22.4'}),true);
 for(const page of [{state_base64:noteState,editor_version:'future-version'},{state_base64:'not base64!',editor_version:'blocksuite-0.22.4'},{state_base64:'AQ==',editor_version:'blocksuite-0.22.4'}])assert.equal(nativePageMayHaveActions(page),true);
});

test('a large set of empty or absent pages needs no editor and no creation',()=>{
 const ids=Array.from({length:57},(_,index)=>'qa-'+index);
 const pages=ids.map(project_id=>({id:'page-'+project_id,project_id,kind:'main',state_base64:null}));
 const result=nativeReadPlan(ids,pages,[],true);
 assert.deepEqual(result.load,[]);assert.equal(result.empty.length,57);
});

test('existing saved pages are read and only real confirmed actions can initialize a page',()=>{
 const pages=[{id:'saved-page',project_id:'saved',kind:'main',state_base64:'AQ=='},{id:'empty-page',project_id:'empty',kind:'main',state_base64:null},{id:'foreign',project_id:'outside',kind:'main',state_base64:'AQ=='}];
 const result=nativeReadPlan(['saved','empty','confirmed'],pages,['confirmed'],true);
 assert.deepEqual(result.load.map(item=>item.projectId),['saved','confirmed']);
 assert.equal(result.load[0].page.id,'saved-page');assert.equal(result.load[1].page,undefined);
 assert.deepEqual(result.empty.map(item=>item.projectId),['empty']);
 assert.deepEqual(nativeReadPlan(['confirmed'],[],['confirmed'],false).load,[]);
});

test('a malformed page catalog is rejected instead of creating fallback pages',()=>{
 assert.throws(()=>nativeReadPlan(['qa'],null,[],true),/pages.*chargée/);
 assert.throws(()=>nativeReadPlan(['qa'],[{id:'missing-project'}],[],true),/pages.*chargée/);
});

const bundled=await build({entryPoints:[fileURLToPath(new URL('./native-actions.ts',import.meta.url))],bundle:true,platform:'node',format:'esm',write:false,logLevel:'silent'});
const native=await import('data:text/javascript;base64,'+Buffer.from(bundled.outputFiles[0].text).toString('base64'));

test('the actual global loader reads the catalog once and mounts no editor for 57 saved empty pages',async()=>{
 const ids=Array.from({length:57},(_,index)=>'qa-'+index);let catalogs=0,details=0,creates=0;
 native.scopeNativeActions('qa-large-set',ids);
 const result=await native.loadNativeActions({pages:async()=>{catalogs++;return ids.map(project_id=>({id:'page-'+project_id,project_id,kind:'main',state_base64:noteState,editor_version:'blocksuite-0.22.4',text:''}));},project:async()=>{details++;throw Error('must not load');},nativePage:async()=>{creates++;throw Error('must not create');}},ids,true,[]);
 assert.deepEqual(result,[]);assert.equal(catalogs,1);assert.equal(details,0);assert.equal(creates,0);
 assert.equal(native.cachedNativeNotes(ids[0]).status,'unavailable');
});

test('a late catalog cannot publish empty projections into a different account',async()=>{
 native.scopeNativeActions('qa-account-a',['qa']);
 const operation=native.loadNativeActions({pages:async()=>[]},['qa'],true,[]);
 native.scopeNativeActions('qa-account-b',['qa']);
 await assert.rejects(operation,/accès actif/);assert.equal(native.cachedNativeNotes('qa').status,'loading');
});

test('the real pages client uses the existing scoped GET without body or mutation',async()=>{
 const original=globalThis.fetch;let captured;
 globalThis.fetch=async(url,options)=>{captured={url,options};return new Response('[]',{headers:{'content-type':'application/json'}});};
 try{assert.deepEqual(await api.pages(),[]);assert.equal(captured.url,'/api/v1/pages');assert.equal(captured.options.method,undefined);assert.equal(captured.options.body,undefined);assert.equal(captured.options.credentials,'same-origin');}
 finally{globalThis.fetch=original;}
});
