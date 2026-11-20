/** A navigation preference only. Every resource remains authorized by the server. */
export function authorizedCommissions(bootstrap){
 const seen=new Set();
 return (Array.isArray(bootstrap?.commissions)?bootstrap.commissions:[]).filter(item=>{
  if(!item||typeof item.id!=='string'||!item.id||seen.has(item.id)||item.active===false||item.can_read!==true||item.capabilities?.can_read===false)return false;
  seen.add(item.id);return true;
 });
}

export function workProfilePreferenceKey(session){
 if(session?.authenticated!==true||session?.public_demo===true||session?.organization_required===true)return null;
 const tenant=session?.actor?.tenant_id,actor=session?.actor?.actor_id;
 if(typeof tenant!=='string'||!tenant||typeof actor!=='string'||!actor)return null;
 return 'travaux:work-profile:'+JSON.stringify([tenant,actor,typeof session?.account?.id==='string'?session.account.id:null]);
}

export function resolveWorkProfile(session,bootstrap,saved,hasProjects=false){
 if(!workProfilePreferenceKey(session))return {status:'inactive',commissionId:'all',changed:false};
 const choices=authorizedCommissions(bootstrap);
 if(typeof saved==='string'&&(choices.some(item=>item.id===saved)||(saved==='all'&&(choices.length>0||hasProjects))||saved==='elu-maire'))return {status:'ready',commissionId:saved,changed:false};
 if(choices.length===1||choices.length>0&&typeof saved==='string'&&saved!=='')return {status:'ready',commissionId:choices[0].id,changed:typeof saved==='string'&&saved!==choices[0].id};
 if(choices.length>1)return {status:'choose',commissionId:null,changed:false};
 if(hasProjects)return {status:'ready',commissionId:'all',changed:Boolean(saved&&saved!=='all')};
 return {status:'unavailable',commissionId:null,changed:Boolean(saved)};
}

export function commissionRequestFilter(bootstrap,commissionId){
 return commissionId!=='all'&&commissionId!=='elu-maire'&&authorizedCommissions(bootstrap).some(item=>item.id===commissionId)?{commission_id:commissionId}:{};
}

function canSelect(snapshot,id){return id==='all'||id==='elu-maire'?true:authorizedCommissions(snapshot.bootstrap).some(item=>item.id===id);}

export async function changeWorkProfile({commissionId,snapshot,preserve,commit}){
 const initial=snapshot();
 if(!canSelect(initial,commissionId))throw Error('Ce profil de travail n’est plus accessible. Actualisez vos accès.');
 await preserve();
 const current=snapshot();
 if(initial.identity!==current.identity)throw Error('Le compte actif a changé. Choisissez un profil dans son espace.');
 if(!canSelect(current,commissionId))throw Error('Ce profil de travail n’est plus accessible. Actualisez vos accès.');
 commit(commissionId);
}
