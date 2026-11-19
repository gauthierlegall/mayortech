const object=value=>value&&typeof value==='object'&&!Array.isArray(value);
const text=(value,max)=>typeof value==='string'&&Boolean(value.trim())&&value.length<=max&&!/[\u0000-\u001f\u007f]/.test(value);
const revision=value=>Number.isSafeInteger(value)&&value>=0;
const invalid=()=>Error('Les demandes reçues sont incomplètes. Actualisez la liste avant de prendre une décision.');
export function canReviewOrganizationRequests(session,bootstrap){
 return session?.authenticated===true&&session?.auth_required===true&&text(session?.account?.id,200)&&session?.organization_required!==true&&bootstrap?.role==='admin'&&bootstrap?.permissions?.organization?.write===true;
}
export function organizationRequestsCatalog(raw){
 if(!object(raw)||!Array.isArray(raw.items))throw invalid();
 if(raw.items.some(item=>!object(item)||!text(item.actor_id,200)||!text(item.display_name,300)||(item.email!==''&&!text(item.email,320))||!['pending','joined','rejected'].includes(item.status)||!revision(item.revision)||!text(item.requested_at,100)||Number.isNaN(Date.parse(item.requested_at))))throw invalid();
 if(new Set(raw.items.map(item=>item.actor_id)).size!==raw.items.length)throw invalid();
 return raw;
}
export async function decideOrganizationRequest({api,request,decision,session,bootstrap,assertCurrent=()=>{}}){
 if(!canReviewOrganizationRequests(session,bootstrap))throw Error('Seul un administrateur de l’organisation peut traiter les demandes d’accès.');
 organizationRequestsCatalog({items:[request]});
 if(request.status!=='pending'||!['approve','reject'].includes(decision))throw Error('Actualisez les demandes avant de prendre une nouvelle décision.');
 assertCurrent();const response=await api.decideOrganizationJoin(request.actor_id,{decision,expected_revision:request.revision});assertCurrent();
 const expected=decision==='approve'?'joined':'rejected';
 if(!object(response)||response.status!==expected||response.member_id!==request.actor_id)throw invalid();
 return response;
}
