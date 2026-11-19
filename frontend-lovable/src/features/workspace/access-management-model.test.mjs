import test from 'node:test';
import assert from 'node:assert/strict';
import * as access from './access-management-model.mjs';

const member={id:'member-a',display_name:'Camille fictive',role:'reader',role_label:'Lecteur',active:false,revision:3,identity_verified:true};
const catalog={items:[member],can_manage:true,capabilities:{identity_provider:true,member_management:true,invitations:false}};
const permissions={organization:{write:true}};
const dossier={project_id:'project-a',revision:4,items:[],administrators_have_access:true};

test('member management requires explicit server capability and organization permission',()=>{
 assert.equal(access.canManageMembers(catalog,permissions),true);
 for(const [data,grants] of [[{...catalog,can_manage:false},permissions],[catalog,{organization:{write:false}}],[{...catalog,capabilities:{identity_provider:false}},permissions]])assert.equal(access.canManageMembers(data,grants),false);
});

test('editable members require real revisions and identities; legacy shared access remains read-only',()=>{
 const parsed=access.memberCatalog(catalog);assert.deepEqual(parsed.items[0],member);
 assert.throws(()=>access.memberCatalog({...catalog,items:[{...member,revision:undefined}]}));
 const legacy=access.memberCatalog({items:[{id:'local',display_name:'Opérateur',role:'operator',kind:'local_operator'}],can_manage:false,capabilities:{identity_provider:false}});
 assert.equal(legacy.can_manage,false);assert.equal(legacy.items[0].revision,null);
});

test('member patch contains only explicit role, active and expected revision, never identity fields',()=>{
 assert.deepEqual(access.memberAccessPatch({...member,email:'private@example.invalid',issuer:'https://id.example.invalid',subject:'private-sub'},{role:'editor',active:true}),{role:'editor',active:true,expected_revision:3});
 for(const draft of [{role:'owner',active:true},{role:'reader',active:'true'},{role:'admin'}])assert.throws(()=>access.memberAccessPatch(member,draft));
});

test('reloading a conflicted member preserves local edits and updates untouched values from server',()=>{
 const merged=access.rebaseMemberDraft(member,{role:'editor',active:false},{...member,role:'admin',active:true,revision:4});
 assert.deepEqual(merged.draft,{role:'editor',active:true});assert.deepEqual(merged.conflicts,['role']);
 assert.equal(member.revision,3);
});

test('member saving uses the original actor identifier and never retries conflicts automatically',async()=>{
 const calls=[],conflict=Object.assign(Error('Version modifiée'),{detail:{code:'stale_revision'}}),draft={role:'editor',active:true};
 await assert.rejects(()=>access.persistMemberAccess({async saveMemberAccess(id,body){calls.push({id,body});throw conflict;}},member,draft),error=>error===conflict);
 assert.deepEqual(calls,[{id:'member-a',body:{role:'editor',active:true,expected_revision:3}}]);assert.deepEqual(draft,{role:'editor',active:true});
});

test('saved identity DTO actor_id is normalized and a changed session cannot publish a response',async()=>{
 const saved=await access.persistMemberAccess({async saveMemberAccess(){return{...member,id:undefined,actor_id:member.id,active:true,revision:4};}},member,{role:'reader',active:true});
 assert.equal(saved.id,member.id);assert.equal(saved.revision,4);
 let current=true;
 await assert.rejects(()=>access.persistMemberAccess({async saveMemberAccess(){current=false;return{...member,revision:4};}},member,{role:'reader',active:true},()=>{if(!current)throw Error('session changed');}),/session changed/);
});

test('project access rejects mismatched project and absent revision rather than inventing zero',()=>{
 assert.equal(access.projectAccessDto(dossier,'project-a').revision,4);
 assert.throws(()=>access.projectAccessDto(dossier,'project-b'));
 assert.throws(()=>access.projectAccessDto({...dossier,revision:undefined},'project-a'));
});

test('only active non-admin members receive explicit dossier grants',()=>{
 const active={...member,active:true};
 assert.deepEqual(access.projectGrantPayload(dossier,active,true),{allowed:true,expected_revision:4});
 assert.throws(()=>access.projectGrantPayload(dossier,member,true));
 assert.throws(()=>access.projectGrantPayload(dossier,{...active,role:'admin'},false));
 assert.throws(()=>access.projectGrantPayload(dossier,active,'true'));
});

test('project access save binds dossier and member and returns next durable revision',async()=>{
 let call;
 const next=await access.persistProjectAccess({async saveProjectAccess(projectId,memberId,body){call={projectId,memberId,body};return{...dossier,revision:5,items:[{id:member.id,display_name:member.display_name,role:member.role}]};}},dossier,{...member,active:true},true);
 assert.deepEqual(call,{projectId:'project-a',memberId:'member-a',body:{allowed:true,expected_revision:4}});assert.equal(next.revision,5);
});

test('reloading dossier access keeps pending choices while removing choices already applied by another admin',()=>{
 const next={...dossier,revision:5,items:[{id:'member-b',display_name:'Autre compte',role:'editor'}]};
 assert.deepEqual(access.rebaseProjectChoices({'member-a':true,'member-b':true},next),{'member-a':true});
});

test('explicit project creation denial overrides broad workspace write capability',()=>{
 assert.equal(access.canCreateProject({access:{project_create:false},permissions:{workspace:{write:true}}}),false);
 assert.equal(access.canCreateProject({access:{project_create:true},permissions:{workspace:{write:true}}}),true);
 assert.equal(access.canCreateProject({permissions:{workspace:{write:true}}}),true);
 assert.equal(access.canCreateProject({permissions:{workspace:{write:false}}}),false);
});

test('context refresh still runs after self-revocation makes member reload fail',async()=>{
 const calls=[];
 await assert.rejects(()=>access.refreshAccessState(async()=>{calls.push('members');throw Error('session revoked');},async()=>{calls.push('context');}),/session revoked/);
 assert.deepEqual(calls,['members','context']);
});
