import assert from 'node:assert/strict';
import test from 'node:test';
import {api as productApi} from '../../../../web/api.js';
import {canLogoutWorkspace,logoutWorkspace} from './workspace-logout-model.mjs';

const session={authenticated:true,auth_required:true,public_demo:false};
function fixture(overrides={}){
 const calls=[];
 return {calls,options:{session,api:{logout:async()=>{calls.push('logout');return {authenticated:false};}},preserve:async()=>{calls.push('save');},assertCurrent:()=>{},onRevoked:()=>{calls.push('revoke-ui');},redirect:()=>{calls.push('redirect');},...overrides}};
}

test('logout is available to individual private sessions and hidden in public demo',()=>{
 assert.equal(canLogoutWorkspace(session),true);
 assert.equal(canLogoutWorkspace({...session,demo:true}),true);
 for(const value of [null,{}, {...session,authenticated:false},{...session,auth_required:false},{...session,public_demo:true}])assert.equal(canLogoutWorkspace(value),false);
});

test('pending edits finish before the session is revoked and navigation begins',async()=>{
 const {calls,options}=fixture();await logoutWorkspace(options);
 assert.deepEqual(calls,['save','logout','revoke-ui','redirect']);
});

test('failed saves keep the session and visible workspace intact',async()=>{
 const {calls,options}=fixture({preserve:async()=>{throw Error('revision_conflict');}});
 await assert.rejects(logoutWorkspace(options),/modifications.*enregistrées/);
 assert.deepEqual(calls,[]);
});

test('a network failure never pretends logout succeeded',async()=>{
 const {calls,options}=fixture({api:{logout:async()=>{throw Error('offline');}}});
 await assert.rejects(logoutWorkspace(options),/déconnexion n’a pas abouti/);
 assert.deepEqual(calls,['save']);
});

test('only the provider authenticated:false contract confirms revocation',async()=>{
 for(const response of [null,{}, {authenticated:true},{authenticated:'false'}]){
  const {calls,options}=fixture({api:{logout:async()=>response}});
  await assert.rejects(logoutWorkspace(options),/déconnexion n’a pas pu être confirmée/);
  assert.deepEqual(calls,['save']);
 }
 const {options}=fixture({api:{logout:async()=>({authenticated:false,extra:'compatible'})}});
 await assert.doesNotReject(logoutWorkspace(options));
});

test('an account switch during saving cannot send logout for the new account',async()=>{
 let current=true;const {calls,options}=fixture({preserve:async()=>{current=false;},assertCurrent:()=>{if(!current)throw Error('account changed');}});
 await assert.rejects(logoutWorkspace(options),/account changed/);assert.deepEqual(calls,[]);
});

test('a late logout response cannot clear or redirect a newer account',async()=>{
 let current=true;const {calls,options}=fixture({api:{logout:async()=>{current=false;return {authenticated:false};}},assertCurrent:()=>{if(!current)throw Error('account changed');}});
 await assert.rejects(logoutWorkspace(options),/account changed/);assert.deepEqual(calls,['save']);
});

test('the real API client sends the existing same-origin DELETE and CSRF header',async()=>{
 const original=globalThis.fetch;let captured;
 globalThis.fetch=async(url,options)=>{captured={url,options};return new Response(JSON.stringify({authenticated:false}),{status:200,headers:{'content-type':'application/json'}});};
 try{
  assert.deepEqual(await productApi.logout(),{authenticated:false});
  assert.equal(captured.url,'/api/v1/session');assert.equal(captured.options.method,'DELETE');
  assert.equal(captured.options.credentials,'same-origin');assert.equal(captured.options.headers['X-Requested-With'],'Travaux');
  assert.equal(captured.options.body,undefined);
 }finally{globalThis.fetch=original;}
});
