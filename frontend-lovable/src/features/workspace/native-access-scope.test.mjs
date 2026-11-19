import assert from 'node:assert/strict';
import test from 'node:test';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';

const bundled=await build({entryPoints:[fileURLToPath(new URL('./native-actions.ts',import.meta.url))],bundle:true,platform:'node',format:'esm',write:false,logLevel:'silent'});
const native=await import('data:text/javascript;base64,'+Buffer.from(bundled.outputFiles[0].text).toString('base64'));

test('an action queued by account A never starts after switching to account B',async()=>{
 let calls=0;const api={project:async()=>{calls++;},nativePage:async()=>{calls++;}};
 native.scopeNativeActions('account-a',['project']);
 const operation=native.createNativeAction(api,'project',{title:'Private draft'});
 native.scopeNativeActions('account-b',['project']);
 await assert.rejects(operation,/session active a changé/);
 assert.equal(calls,0);assert.deepEqual(native.cachedNativeActions(['project']),[]);
 assert.equal(native.cachedNativeNotes('project').status,'loading');
});

test('an obsolete project grant cannot start a hidden editor or a page write',async()=>{
 let calls=0;const api={project:async()=>{calls++;},nativePage:async()=>{calls++;}};
 native.scopeNativeActions('same-account',['retained']);
 await assert.rejects(native.createNativeAction(api,'revoked',{title:'Forbidden'}),/accès actif a changé/);
 assert.equal(calls,0);
});

test('a mounted editor refuses a late save after revocation but a retained project remains editable',()=>{
 native.scopeNativeActions('editor-account',['retained','revoked']);
 const retained=native.nativeAccessGuard('retained'),revoked=native.nativeAccessGuard('revoked');
 native.scopeNativeActions('editor-account',['retained']);
 assert.doesNotThrow(retained);assert.throws(revoked,/accès actif a changé/);
 native.scopeNativeActions('other-account',['retained']);
 assert.throws(retained,/accès actif a changé/);
});
