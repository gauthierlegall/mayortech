/** Explicit API double. loadWorkspace, QueryClient and WorkspaceProvider are real. */
export const control={actor:'account-a',requests:[] as string[],grantsScenario:new URLSearchParams(location.search).get('scenario')==='grants',allowed:['retained','neighbor'],failDetails:false};
const record=(name:string)=>{control.requests.push(name+':'+control.actor);};
export const api={
 async session(){record('session');return {authenticated:true,auth_required:true,organization_required:false,actor:{tenant_id:'fixture-tenant',actor_id:control.actor,role:'editor'},account:{id:control.actor,display_name:control.actor}};},
 async bootstrap(){record('bootstrap');if(control.actor==='account-b')throw Error('Chargement métier fictif B impossible');return {permissions:{workspace:{read:true,write:true},mail:{read:true},organization:{read:true},members:{read:true},audit:{read:true}}};},
 async projects(){record('projects');return control.grantsScenario?control.allowed.map(id=>({id,name:'Dossier fictif '+id,reference:'FIXTURE-'+id})):[];},
 async project(id:string){record('project-'+id);if(control.failDetails)throw Error('Détail fictif du dossier conservé indisponible');return {id,name:'Dossier fictif '+id,actions:[],notes:[],sources:[],facts:[]};},
 async documents(){return [];},
 async mailboxMessages(){return {items:[],total:0};},async summaries(){return [];},
 async organization(){return {name:'Contenu métier fictif du compte A'};},
 async organizationMembers(){return {items:[]};},async organizationAudit(){return [];},
};
