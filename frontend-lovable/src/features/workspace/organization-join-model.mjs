export const ORGANIZATION_JOIN_ERROR='La demande n’a pas pu être confirmée. Actualisez son état avant de réessayer.';
export const ORGANIZATION_PENDING='Votre demande d’accès attend l’autorisation de l’administrateur.';
export const ORGANIZATION_REJECTED='Votre demande d’accès a été refusée. Contactez l’administrateur de l’organisation.';
const invalid=()=>Error('La liste des organisations est incomplète. Actualisez-la avant de continuer.');
const object=value=>value&&typeof value==='object'&&!Array.isArray(value);
const text=(value,max)=>typeof value==='string'&&value.trim()&&value.length<=max&&!/[\u0000-\u001f\u007f]/.test(value);
const states=['joined','pending','rejected','not_joined'];

export function requiresOrganization(session){return session?.authenticated===true&&session?.organization_required===true;}
export function organizationsCatalog(raw){
 if(!object(raw)||!Array.isArray(raw.items)||typeof raw.organization_required!=='boolean')throw invalid();
 if(raw.items.some(item=>!object(item)||!text(item.id,200)||!text(item.name,300)||typeof item.is_test!=='boolean'||typeof item.can_self_join!=='boolean'||typeof item.can_enter!=='boolean'||!states.includes(item.membership_status)))throw invalid();
 if(new Set(raw.items.map(item=>item.id)).size!==raw.items.length)throw invalid();
 if(raw.test_join_code!==undefined&&(typeof raw.test_join_code!=='string'||!raw.items.some(item=>item.is_test===true)||! /^[A-Z0-9-]{6,64}$/.test(raw.test_join_code)))throw invalid();
 return raw;
}
export function organizationAction(item){
 if(item.membership_status==='pending')return 'pending';
 if(item.membership_status==='rejected')return 'rejected';
 if(item.membership_status==='joined')return item.can_enter===true?'enter':'unavailable';
 if(item.membership_status==='not_joined')return 'code';
 return 'unavailable';
}
export function organizationCode(value){
 if(typeof value!=='string'||!value.trim())throw Error('Saisissez le code de votre organisation.');
 if(/[^\x20-\x7e]/.test(value))throw Error('Le code doit contenir de 6 à 64 lettres, chiffres ou tirets, sans espace.');
 const code=value.trim().toUpperCase();
 if(!/^[A-Z0-9-]{6,64}$/.test(code))throw Error('Le code doit contenir de 6 à 64 lettres, chiffres ou tirets, sans espace.');
 return code;
}
function joinResult(response,organizationId){
 const selected=response?.organization;
 if(!object(response)||!['joined','pending','rejected'].includes(response.status)||!object(selected)||!text(selected.id,200)||!text(selected.name,300)||typeof selected.is_test!=='boolean'||(organizationId!==undefined&&selected.id!==organizationId))throw Error(ORGANIZATION_JOIN_ERROR);
 return {status:response.status,organization:{id:selected.id,name:selected.name,is_test:selected.is_test},message:response.status==='pending'?ORGANIZATION_PENDING:response.status==='rejected'?ORGANIZATION_REJECTED:'L’accès à l’organisation est autorisé.'};
}
export async function requestOrganizationCode({api,code,assertCurrent=()=>{}}){
 const normalized=organizationCode(code);assertCurrent();
 const response=await api.joinOrganizationCode(normalized);assertCurrent();
 return joinResult(response);
}
export async function requestOrganizationJoin({api,catalog,organizationId,assertCurrent=()=>{}}){
 organizationsCatalog(catalog);const item=catalog.items.find(value=>value.id===organizationId);
 if(!item||organizationAction(item)!=='enter')throw Error('Un code est nécessaire pour demander l’accès à une organisation.');
 assertCurrent();let response;
 try{response=await api.joinOrganization(item.id);}catch{throw Error(ORGANIZATION_JOIN_ERROR);}
 assertCurrent();
 const result=joinResult(response,item.id);
 if(result.status!=='joined')throw Error(ORGANIZATION_JOIN_ERROR);
 return result;
}
