/** Read projections of FastAPI records. Editable rows remain in the native document. */
export type ActionStatus = 'À faire' | 'En cours' | 'En attente' | 'Terminé';
export type ProjectStatus = 'En cours' | 'À préparer' | 'En attente' | 'Bloqué' | 'Annulé' | 'Terminé' | '';
export interface Project {id:string;title:string;ref:string;location:string;category:string;status:ProjectStatus;owner:string;initials:string;company:string;delivery:string;deadline?:string;requestDate?:string;requester?:string;priority?:string;description:string;favorite:boolean;progress:string;pendingCount:number;sourceCount:number;updatedAt:string;storyline:boolean}
export interface Action {id:string;projectId:string;title:string;description:string;owner:string;due:string;priority:string;status:ActionStatus|'';source?:string;kind:'confirmed_fact';editable:false}
export interface Message {id:string;projectId:string;sender:string;email:string;subject:string;body:string;date:string;read:boolean;starred:boolean;folder:string;attachment?:string}
export interface Document {id:string;documentId:string|null;projectId:string;name:string;version:null;status:string;source:string;sourceId:string;parentSourceId:string;previewSourceId:string;date:string;amount:string;file:string;available:boolean;mediaType:string;sha256:string;size:number|null}
export interface History {id:string;projectId:string;title:string;detail:string;date:string;source?:string;author:string}
export interface Summary {id:string;projectId:string;date:string;text:string;source:string;status:string;stale:boolean;coverage:string}
export interface Member {id:string;name:string;service:string;role:string;active:boolean}
export interface Workspace {projects:Project[];actions:Action[];messages:Message[];documents:Document[];history:History[];notes:Record<string,string>;summaries:Summary[];accent:string;organization:string;members:Member[];messageTotal:number;messagesComplete:boolean}
export const statuses:ActionStatus[]=['À faire','En cours','En attente','Terminé'];
export const text=(value:unknown):string=>typeof value==='string'?value:'';
export const list=(value:any):any[]=>Array.isArray(value)?value:Array.isArray(value?.items)?value.items:[];
export function emptyWorkspace():Workspace{return{projects:[],actions:[],messages:[],documents:[],history:[],notes:{},summaries:[],accent:'',organization:'',members:[],messageTotal:0,messagesComplete:true};}
export function formatDate(value?:string|null,fallback='Non renseignée',includeYear=false):string{
 if(typeof value!=='string'||!value.trim())return fallback;
 const civil=/^(\d{4})-(\d{2})-(\d{2})$/.exec(value);let date:Date;
 if(civil){date=new Date(`${value}T12:00:00Z`);if(date.getUTCFullYear()!==Number(civil[1])||date.getUTCMonth()+1!==Number(civil[2])||date.getUTCDate()!==Number(civil[3]))return fallback;}
 else{if(!/^\d{4}-\d{2}-\d{2}T/.test(value))return fallback;date=new Date(value);}
 return Number.isFinite(date.getTime())?new Intl.DateTimeFormat('fr-FR',{day:'numeric',month:'long',year:includeYear?'numeric':undefined,timeZone:'Europe/Paris'}).format(date):fallback;
}
function factText(value:any):string{return text(value)||text(value?.text)||text(value?.date)||text(value?.value);}
function confirmedFact(detail:any,keys:string[]):string{const fact=list(detail?.facts||detail?.confirmed_facts).find(row=>keys.includes(text(row.field))&&(!row.status||row.status==='accepted'));return factText(fact?.value);}
export function projectFromApi(base:any,detail:any={}):Project{
 const raw={...base,...(detail?.project||{}),...detail};
 const property=(key:string,fallback:string)=>typeof raw.properties?.values?.[key]==='string'?raw.properties.values[key]:fallback;
 const owner=property('service_owner',text(raw.owner)||confirmedFact(detail,['owner','responsible','assignee']));
 const statuses:Record<string,ProjectStatus>={active:'En cours',in_progress:'En cours',planned:'À préparer',pending:'À préparer',on_hold:'En attente',blocked:'Bloqué',cancelled:'Annulé',completed:'Terminé',closed:'Terminé',done:'Terminé','En cours':'En cours','À préparer':'À préparer','Terminé':'Terminé','En attente':'En attente','Bloqué':'Bloqué','Annulé':'Annulé'};
 return{id:text(raw.id),title:text(raw.name)||text(raw.title),ref:text(raw.reference)||text(raw.ref),location:property('location',text(raw.location)||confirmedFact(detail,['location'])),category:property('category',text(raw.category)||confirmedFact(detail,['category'])),status:statuses[text(raw.status)]||'',owner,initials:owner.trim().split(/\s+/).filter(Boolean).slice(0,2).map(part=>Array.from(part)[0]||'').join('').toLocaleUpperCase('fr'),company:property('contractor',text(raw.company)||confirmedFact(detail,['contractor'])),delivery:text(raw.delivery_date)||confirmedFact(detail,['delivery_date']),deadline:property('deadline',confirmedFact(detail,['deadline'])),requestDate:property('request_date',''),requester:property('requester',''),priority:property('priority',''),description:text(raw.description),favorite:['TRV-2026-042','TRV-2026-038'].includes(text(raw.reference))&&list(detail?.sources).some(source=>source.metadata?.storyline_id==='lovable-travaux-v1'),storyline:list(detail?.sources).some(source=>source.metadata?.storyline_id==='lovable-travaux-v1'),progress:text(raw.progress)||confirmedFact(detail,['progress']),pendingCount:Number.isFinite(raw.pending_count)?raw.pending_count:list(detail?.pending).length,sourceCount:Number.isFinite(raw.source_count)?raw.source_count:list(detail?.sources).length,updatedAt:text(raw.updated_at)||text(raw.created_at)};
}
export function confirmedActionsFromApi(detail:any,projectId:string):Action[]{
 return list(detail?.actions).filter(action=>(!action.status||action.status==='accepted')&&text(action.field).startsWith('action.')).map((action):Action=>{const value=action.value;const title=text(value)||text(value?.title)||text(value?.action)||text(value?.description);const operational=text(value?.status);const source=text(action.source_id)||text(action.evidence?.[0]?.source_id);return{id:text(action.id),projectId,title,description:text(value?.description),owner:text(value?.owner)||text(value?.assignee),due:text(value?.due_date)||text(value?.deadline),priority:text(value?.priority),status:statuses.includes(operational as ActionStatus)?operational as ActionStatus:'',...(source?{source}:{}),kind:'confirmed_fact',editable:false};}).filter(action=>action.id&&action.title);
}
export function documentFromApi(raw:any,projectId:string):Document{
 const sourceId=text(raw.source_id),parentSourceId=text(raw.parent_source_id),documentId=text(raw.id)||null;const file=raw.available===true&&documentId?`/api/v1/documents/${encodeURIComponent(documentId)}/download`:'';
 return{id:documentId||`unavailable:${sourceId}:${text(raw.sha256)||text(raw.filename)}`,documentId,projectId,name:text(raw.filename),version:null,status:file?'Original disponible':'Original indisponible',source:parentSourceId||sourceId,sourceId,parentSourceId,previewSourceId:raw.text_available===true?text(raw.preview_source_id):'',date:text(raw.created_at),amount:'',file,available:Boolean(file),mediaType:text(raw.media_type),sha256:text(raw.sha256),size:Number.isFinite(raw.size)?raw.size:null};
}
export function messageFromApi(raw:any,attachment?:string):Message{
 const sender=text(raw.sender);const email=text(raw.email)||/<([^<>]+)>/.exec(sender)?.[1]||(sender.includes('@')?sender:'');
 return{id:text(raw.id),projectId:text(raw.project_id)||text(raw.project_ids?.[0]),sender,email,subject:text(raw.subject),body:text(raw.body),date:text(raw.received_at)||text(raw.created_at),read:raw.read===true,starred:raw.starred===true,folder:text(raw.folder)||'inbox',...(attachment?{attachment}:{})};
}
const eventLabels:Record<string,string>={'candidate.accepted':'Information confirmée','candidate.rejected':'Proposition écartée','candidate.corrected':'Proposition corrigée','note.added':'Note humaine ajoutée','workspace.note_imported':'Page de chantier enregistrée','summary.created':'Récapitulatif préparé','summary.approved':'Récapitulatif validé','summary.cancelled':'Récapitulatif annulé','document.stored':'Original conservé','organization.updated':'Profil de l’organisation modifié'};
export function historyFromApi(raw:any,projectId=''):History{const source=text(raw.provenance?.source_id);return{id:text(raw.id),projectId:text(raw.project_id)||projectId,title:eventLabels[text(raw.action)||text(raw.event_type)]||'Évolution du dossier',detail:text(raw.provenance?.source_title),date:text(raw.created_at),author:text(raw.actor_label),...(source?{source}:{})};}
