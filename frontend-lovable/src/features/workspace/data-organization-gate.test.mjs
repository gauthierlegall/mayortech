import assert from 'node:assert/strict';
import test from 'node:test';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';

const bundled=await build({entryPoints:[fileURLToPath(new URL('./data.ts',import.meta.url))],bundle:true,platform:'node',format:'esm',write:false,logLevel:'silent'});
const {loadWorkspace}=await import('data:text/javascript;base64,'+Buffer.from(bundled.outputFiles[0].text).toString('base64'));

test('an authenticated account awaiting organization choice cannot request bootstrap or any business data',async()=>{
 const calls=[],session={authenticated:true,organization_required:true,account:{id:'opaque-account',display_name:'Compte fictif'}};
 const client=new Proxy({session:async()=>{calls.push('session');return session;}},{get(target,key){return key in target?target[key]:async()=>{calls.push(key);throw Error('Business API requested before organization choice: '+key);};}});
 let result;
 await assert.doesNotReject(async()=>{result=await loadWorkspace(client);});
 assert.deepEqual(calls,['session']);assert.equal(result.session,session);assert.equal(result.bootstrap,null);assert.deepEqual(result.state.projects,[]);assert.deepEqual(result.state.messages,[]);
});
