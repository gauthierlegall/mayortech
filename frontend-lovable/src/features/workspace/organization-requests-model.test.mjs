import assert from 'node:assert/strict';
import test from 'node:test';
import * as requests from './organization-requests-model.mjs';

const request={actor_id:'new-account',display_name:'Camille Test',email:'camille@example.test',status:'pending',revision:2,requested_at:'2026-11-18T09:00:00Z'};
const session={authenticated:true,auth_required:true,account:{id:'admin-account'},actor:{actor_id:'admin-account',tenant_id:'test-town'}};
const bootstrap={role:'admin',permissions:{organization:{write:true}}};

test('request controls require an authenticated administrator and organization permission',()=>{
 assert.equal(requests.canReviewOrganizationRequests(session,bootstrap),true);
 for(const denied of [null,{...session,authenticated:false},{...session,organization_required:true},{...session,auth_required:false},{...session,account:null},{...session,account:{id:''}}])assert.equal(requests.canReviewOrganizationRequests(denied,bootstrap),false);
 for(const denied of [{...bootstrap,role:'editor'},{...bootstrap,role:'reader'},{...bootstrap,permissions:{organization:{write:false}}},null])assert.equal(requests.canReviewOrganizationRequests(session,denied),false);
});
test('request catalog validates identities, status, date and integer revisions before rendering actions',()=>{
 assert.deepEqual(requests.organizationRequestsCatalog({items:[request]}),{items:[request]});
 for(const item of [{...request,actor_id:''},{...request,display_name:null},{...request,email:42},{...request,revision:-1},{...request,revision:1.5},{...request,status:'admin'},{...request,requested_at:'bad date'}])assert.throws(()=>requests.organizationRequestsCatalog({items:[item]}));
 assert.throws(()=>requests.organizationRequestsCatalog({items:[request,request]}));
 assert.equal(requests.organizationRequestsCatalog({items:[{...request,email:''}]}).items[0].actor_id,'new-account');
});
test('approve and reject decisions send the request revision and validate the resulting membership',async()=>{
 for(const [decision,status,member_id] of [['approve','joined',request.actor_id],['reject','rejected',request.actor_id]]){
  const calls=[];const api={async decideOrganizationJoin(...args){calls.push(args);return{status,member_id};}};
  const result=await requests.decideOrganizationRequest({api,request,decision,session,bootstrap});
  assert.equal(result.status,status);assert.deepEqual(calls,[[request.actor_id,{decision,expected_revision:2}]]);
 }
});
test('non-admin, completed requests and invalid decisions cannot invoke approval',async()=>{
 let called=false;const api={decideOrganizationJoin(){called=true;}};
 for(const options of [{bootstrap:{...bootstrap,role:'editor'}},{request:{...request,status:'joined'}},{decision:'admin'},{bootstrap:{...bootstrap,permissions:{organization:{write:false}}}}])await assert.rejects(()=>requests.decideOrganizationRequest({api,request,decision:'approve',session,bootstrap,...options}));
 assert.equal(called,false);
});
test('stale revision propagates so the interface requires a reload before another decision',async()=>{
 const stale=Object.assign(Error('Request changed'),{status:409,detail:{code:'stale_revision'}});
 await assert.rejects(()=>requests.decideOrganizationRequest({api:{async decideOrganizationJoin(){throw stale;}},request,decision:'approve',session,bootstrap}),failure=>failure===stale);
});
test('wrong status, different member and changed session responses fail closed',async()=>{
 for(const response of [{status:'rejected',member_id:null},{status:'joined',member_id:'another'},null])await assert.rejects(()=>requests.decideOrganizationRequest({api:{async decideOrganizationJoin(){return response;}},request,decision:'approve',session,bootstrap}));
 let current=true;await assert.rejects(()=>requests.decideOrganizationRequest({api:{async decideOrganizationJoin(){current=false;return{status:'joined',member_id:request.actor_id};}},request,decision:'approve',session,bootstrap,assertCurrent(){if(!current)throw Error('account changed');}}),/account changed/);
});
test('a refusal receipt must identify the exact account that was refused',async()=>{
 for(const member_id of [null,undefined,'another'])await assert.rejects(()=>requests.decideOrganizationRequest({api:{async decideOrganizationJoin(){return{status:'rejected',member_id};}},request,decision:'reject',session,bootstrap}));
});
