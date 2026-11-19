import assert from 'node:assert/strict';
import test from 'node:test';
import {authorizedCommissions,workProfilePreferenceKey,resolveWorkProfile,commissionRequestFilter,changeWorkProfile} from './work-profile-model.mjs';

const session={authenticated:true,auth_required:true,account:{id:'account-a'},actor:{tenant_id:'tenant-a',actor_id:'actor-a'}};
const commission=(id,can_read=true)=>({id,name:id,can_read,can_edit:false,capabilities:{can_read,can_edit:false}});
const bootstrap={commissions:[commission('commission-1'),commission('commission-3')]};
const snapshot=()=>({identity:'identity-a',session,bootstrap,hasProjects:true});

test('only explicit readable active commissions are offered, regardless of global role',()=>{
 const raw={role:'admin',commissions:[commission('allowed'),commission('denied',false),{id:'missing',role:'admin'},{...commission('conflict'),capabilities:{can_read:false}},{...commission('inactive'),active:false},commission('allowed')]};
 assert.deepEqual(authorizedCommissions(raw).map(item=>item.id),['allowed']);
});

test('preferences are scoped to tenant and authenticated identity, never the old shared key',()=>{
 const key=workProfilePreferenceKey(session);
 assert.match(key,/travaux:work-profile:/);
 assert.notEqual(key,workProfilePreferenceKey({...session,account:{id:'account-b'}}));
 assert.notEqual(key,workProfilePreferenceKey({...session,actor:{...session.actor,tenant_id:'tenant-b'}}));
 assert.notEqual(key,workProfilePreferenceKey({...session,actor:{...session.actor,actor_id:'actor-b'}}));
 assert.equal(workProfilePreferenceKey({...session,authenticated:false}),null);
 assert.equal(workProfilePreferenceKey({...session,organization_required:true}),null);
});

test('multiple authorized commissions require a first choice, one skips the step',()=>{
 assert.equal(resolveWorkProfile(session,bootstrap,null).status,'choose');
 assert.deepEqual(resolveWorkProfile(session,{commissions:[commission('only')]},null),{status:'ready',commissionId:'only',changed:false});
 assert.equal(resolveWorkProfile(session,bootstrap,'commission-3').commissionId,'commission-3');
});

test('revoked and forged preferences fall back to an authorized commission',()=>{
 assert.deepEqual(resolveWorkProfile(session,bootstrap,'forged'),{status:'ready',commissionId:'commission-1',changed:true});
 assert.deepEqual(commissionRequestFilter(bootstrap,'forged'),{});
 assert.deepEqual(commissionRequestFilter(bootstrap,'commission-3'),{commission_id:'commission-3'});
});

test('direct dossier grants remain reachable without granting commission membership',()=>{
 const denied={commissions:[commission('commission-4',false)]};
 assert.deepEqual(resolveWorkProfile(session,denied,null,true),{status:'ready',commissionId:'all',changed:false});
 assert.equal(resolveWorkProfile(session,denied,null,false).status,'unavailable');
 assert.equal(resolveWorkProfile(session,bootstrap,'all',true).commissionId,'all');
});

test('organization onboarding and the public demonstration do not gain an extra gate',()=>{
 assert.equal(resolveWorkProfile({...session,organization_required:true},bootstrap,null).status,'inactive');
 assert.equal(resolveWorkProfile({...session,public_demo:true},bootstrap,null).status,'inactive');
});

test('changing profile waits for pending panel saves and a conflict leaves selection unchanged',async()=>{
 const calls=[];
 await changeWorkProfile({commissionId:'commission-3',snapshot,preserve:async()=>calls.push('save'),commit:id=>calls.push(id)});
 assert.deepEqual(calls,['save','commission-3']);
 await assert.rejects(changeWorkProfile({commissionId:'commission-1',snapshot,preserve:async()=>{throw Error('revision_conflict');},commit:()=>calls.push('wrong')}),/revision_conflict/);
 assert.deepEqual(calls,['save','commission-3']);
});

test('a late profile change cannot cross identities or newly revoked permissions',async()=>{
 let current=snapshot(),committed=false;
 await assert.rejects(changeWorkProfile({commissionId:'commission-3',snapshot:()=>current,preserve:async()=>{current={...current,identity:'identity-b'};},commit:()=>{committed=true;}}),/compte actif/);
 assert.equal(committed,false);
 current=snapshot();
 await assert.rejects(changeWorkProfile({commissionId:'commission-3',snapshot:()=>current,preserve:async()=>{current={...current,bootstrap:{commissions:[commission('commission-1')]}};},commit:()=>{committed=true;}}),/plus accessible/);
 assert.equal(committed,false);
});
