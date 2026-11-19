import assert from 'node:assert/strict';
import test from 'node:test';
import * as org from './organization-join-model.mjs';

const organization={id:'test-town',name:'Mairie test',is_test:true};
const item={...organization,can_self_join:true,membership_status:'not_joined',can_enter:false};
const catalog={organization_required:true,items:[item],test_join_code:'MAIRIE-TEST'};

test('organization gate requires an authenticated account and the server gate',()=>{
 assert.equal(org.requiresOrganization({authenticated:true,organization_required:true}),true);
 for(const session of [null,{authenticated:false,organization_required:true},{authenticated:true,organization_required:false}])assert.equal(org.requiresOrganization(session),false);
});
test('catalog accepts refusal and a test code while rejecting malformed status or flags',()=>{
 assert.deepEqual(org.organizationsCatalog({...catalog,items:[{...item,membership_status:'rejected'}]}),{...catalog,items:[{...item,membership_status:'rejected'}]});
 for(const raw of [{...catalog,items:[item,item]},{...catalog,items:[{...item,name:''}]},{...catalog,items:[{...item,can_enter:'true'}]},{...catalog,items:[{...item,membership_status:'admin'}]},{...catalog,test_join_code:42}])assert.throws(()=>org.organizationsCatalog(raw));
});
test('only a joined membership can open directly; first joins require a code',()=>{
 assert.equal(org.organizationAction(item),'code');
 assert.equal(org.organizationAction({...item,membership_status:'pending'}),'pending');
 assert.equal(org.organizationAction({...item,membership_status:'rejected'}),'rejected');
 assert.equal(org.organizationAction({...item,membership_status:'joined',can_enter:true}),'enter');
 assert.equal(org.organizationAction({...item,membership_status:'joined',can_enter:false}),'unavailable');
});
test('code is normalized at its transport boundary and blank or invalid input never sends',async()=>{
 const calls=[];const api={async joinOrganizationCode(code){calls.push(code);return{status:'joined',organization,message:'ignored'};}};
 const result=await org.requestOrganizationCode({api,code:'  mairie-test  '});
 assert.equal(result.status,'joined');assert.deepEqual(calls,['MAIRIE-TEST']);
 for(const code of ['', '   ','abc','Mairie test','MAIRIE-TÉST','MAIRIE-TEſT','MAIRIE-TEßT','\tMAIRIE-TEST','MAIRIE-TEST\n','A'.repeat(65),null])await assert.rejects(()=>org.requestOrganizationCode({api,code}));
 assert.equal(calls.length,1);
});
test('pending and rejected code responses never claim that access is granted',async()=>{
 for(const status of ['pending','rejected']){
  const result=await org.requestOrganizationCode({api:{async joinOrganizationCode(){return{status,organization,message:'synthetic-token-must-not-be-reflected'};}},code:'MAIRIE-TEST'});
  assert.equal(result.status,status);assert.equal(result.message.includes('synthetic-token'),false);
 }
});
test('malformed code results fail closed and an account switch discards the response',async()=>{
 for(const result of [{status:'joined',organization:{id:'',name:'Mairie',is_test:true}},{status:'joined',organization:{...organization,is_test:'yes'}},{status:'admin',organization},null])await assert.rejects(()=>org.requestOrganizationCode({api:{async joinOrganizationCode(){return result;}},code:'MAIRIE-TEST'}));
 let current=true;
 await assert.rejects(()=>org.requestOrganizationCode({api:{async joinOrganizationCode(){current=false;return{status:'joined',organization};}},code:'MAIRIE-TEST',assertCurrent(){if(!current)throw Error('account changed');}}),/account changed/);
});
test('existing access uses its server identifier; a first join and pending or rejected access do not send',async()=>{
 const joinedCatalog={...catalog,items:[{...item,membership_status:'joined',can_enter:true}]};const calls=[];
 const api={async joinOrganization(...args){calls.push(args);return{status:'joined',organization};}};
 assert.equal((await org.requestOrganizationJoin({api,catalog:joinedCatalog,organizationId:item.id})).status,'joined');
 assert.deepEqual(calls,[[item.id]]);
 for(const membership_status of ['not_joined','pending','rejected'])await assert.rejects(()=>org.requestOrganizationJoin({api,catalog:{...catalog,items:[{...item,membership_status}]},organizationId:item.id}));
 assert.equal(calls.length,1);
});
test('an entry response for another organization is rejected before it can open',async()=>{
 await assert.rejects(()=>org.requestOrganizationJoin({api:{async joinOrganization(){return{status:'joined',organization:{...organization,id:'other'}};}},catalog:{...catalog,items:[{...item,membership_status:'joined',can_enter:true}]},organizationId:item.id}));
});
