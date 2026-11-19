import test from 'node:test';
import assert from 'node:assert/strict';
import {workspaceMailIdentity,mailFolderUnread} from './mail-navigation-state.mjs';

const actor=(tenant,actor,auth=true)=>({actor:{tenant_id:tenant,actor_id:actor},auth_required:auth});

test('folder count from another actor is rejected rather than relabelled for the receiver',()=>{
 const previous=workspaceMailIdentity(actor('tenant','alice'));
 const current=workspaceMailIdentity(actor('tenant','bob'));
 assert.equal(mailFolderUnread({identity:previous,items:[{id:'inbox',unread:17}]},current),null);
});

test('a scoped zero unread count is accepted as a value',()=>{
 const identity=workspaceMailIdentity(actor('tenant','alice'));
 assert.equal(mailFolderUnread({identity,items:[{id:'inbox',unread:0}]},identity),0);
 assert.equal(mailFolderUnread({identity,items:[{id:'inbox',unread:8}]},identity),8);
});

test('untagged, malformed and invalid counts cannot override the navigation badge',()=>{
 const identity=workspaceMailIdentity(actor('tenant','alice'));
 for(const detail of [null,undefined,[],[{id:'inbox',unread:4}],{},
  {items:[{id:'inbox',unread:4}]},{identity,items:{}},{identity,items:[]},
  ...[-1,1.5,NaN,Infinity,Number.MAX_SAFE_INTEGER+1,'4',null].map(unread=>({identity,items:[{id:'inbox',unread}]}))]){
  assert.equal(mailFolderUnread(detail,identity),null);
 }
 assert.equal(mailFolderUnread({items:[{id:'inbox',unread:4}]},undefined),null);
});

test('structured identity prevents colon-delimited tenant and actor collisions',()=>{
 const first=workspaceMailIdentity(actor('tenant:unit','person'));
 const second=workspaceMailIdentity(actor('tenant','unit:person'));
 assert.notEqual(first,second);
 assert.equal(mailFolderUnread({identity:first,items:[{id:'inbox',unread:5}]},second),null);
 assert.notEqual(workspaceMailIdentity(actor('tenant','person',true)),workspaceMailIdentity(actor('tenant','person',false)));
});

test('an absent session has a stable explicit identity without throwing',()=>{
 assert.equal(workspaceMailIdentity(undefined),JSON.stringify(['','',false]));
 assert.equal(workspaceMailIdentity({}),workspaceMailIdentity(undefined));
});
