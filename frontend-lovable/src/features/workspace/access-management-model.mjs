const ROLES=['admin','editor','reader'];
export const accessRoleLabels={admin:'Administrateur',editor:'Éditeur',reader:'Lecteur'};
const invalid=()=>Error('Les accès reçus sont incomplets. Rechargez la liste avant de modifier des droits.');
const object=value=>value&&typeof value==='object'&&!Array.isArray(value);
const revision=value=>Number.isSafeInteger(value)&&value>=0;

export function canManageMembers(catalog,permissions){
 return catalog?.can_manage===true&&catalog?.capabilities?.identity_provider===true&&catalog?.capabilities?.member_management===true&&permissions?.organization?.write===true;
}
function memberDto(raw){
 if(!object(raw)||typeof (raw.id||raw.actor_id)!=='string'||!(raw.id||raw.actor_id)||typeof raw.display_name!=='string')throw invalid();
 const result={...raw,id:raw.id||raw.actor_id,revision:revision(raw.revision)?raw.revision:null,active:typeof raw.active==='boolean'?raw.active:null};
 delete result.actor_id;return result;
}
export function memberCatalog(raw){
 if(!object(raw)||!Array.isArray(raw.items))throw invalid();
 const items=raw.items.map(memberDto);
 if(new Set(items.map(item=>item.id)).size!==items.length)throw invalid();
 if(raw.can_manage===true&&items.some(item=>!ROLES.includes(item.role)||item.active===null||item.revision===null))throw invalid();
 return {...raw,items,can_manage:raw.can_manage===true};
}
export function memberAccessPatch(member,draft){
 if(!revision(member.revision)||!ROLES.includes(draft.role)||typeof draft.active!=='boolean')throw invalid();
 return {role:draft.role,active:draft.active,expected_revision:member.revision};
}
export function rebaseMemberDraft(baseline,draft,latest){
 const result={role:latest.role,active:latest.active},conflicts=[];
 for(const key of ['role','active'])if(draft[key]!==baseline[key]){
  result[key]=draft[key];
  if(latest[key]!==baseline[key]&&latest[key]!==draft[key])conflicts.push(key);
 }
 return {draft:result,conflicts};
}
export async function persistMemberAccess(api,member,draft,assertCurrent=()=>{}){
 const payload=memberAccessPatch(member,draft);assertCurrent();
 const response=await api.saveMemberAccess(member.id,payload);assertCurrent();
 const saved=memberDto(response);
 if(saved.id!==member.id||!ROLES.includes(saved.role)||typeof saved.active!=='boolean'||saved.revision===null||saved.revision<member.revision)throw invalid();
 return saved;
}
export function projectAccessDto(raw,projectId){
 if(!object(raw)||raw.project_id!==projectId||!revision(raw.revision)||!Array.isArray(raw.items)||raw.administrators_have_access!==true)throw invalid();
 if(raw.items.some(item=>!object(item)||typeof item.id!=='string'||!item.id||typeof item.display_name!=='string'||!ROLES.includes(item.role))||new Set(raw.items.map(item=>item.id)).size!==raw.items.length)throw invalid();
 return raw;
}
export function projectGrantPayload(access,member,allowed){
 projectAccessDto(access,access.project_id);
 if(member.active!==true||!['editor','reader'].includes(member.role)||typeof allowed!=='boolean')throw Error('Choisissez un membre actif, lecteur ou éditeur. Les administrateurs disposent déjà de tous les dossiers.');
 return {allowed,expected_revision:access.revision};
}
export async function persistProjectAccess(api,access,member,allowed,assertCurrent=()=>{}){
 const payload=projectGrantPayload(access,member,allowed);assertCurrent();
 const response=await api.saveProjectAccess(access.project_id,member.id,payload);assertCurrent();
 const saved=projectAccessDto(response,access.project_id);
 if(saved.revision<access.revision)throw invalid();
 return saved;
}
export function rebaseProjectChoices(choices,access){
 const granted=new Set(access.items.map(item=>item.id));
 return Object.fromEntries(Object.entries(choices).filter(([id,allowed])=>allowed!==granted.has(id)));
}
export function canCreateProject(bootstrap){
 return bootstrap?.access?.project_create!==false&&bootstrap?.permissions?.workspace?.write===true;
}
export async function refreshAccessState(reload,refresh){
 try{return await reload();}finally{await refresh();}
}
