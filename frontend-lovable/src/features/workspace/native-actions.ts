import {actionInputs} from '../../../../web/workspace-model.js';
import {fieldReportAction,fieldReportLink,type FieldReportActionSource} from './field-report-action.mjs';
import {nativeReadPlan,type NativeReadPage} from './native-read-plan.mjs';

export interface NativeAction {id:string;projectId:string;databaseId:string;title:string;description:string;status:string;owner:string;start?:string;due:string;progress?:number;priority:string;source?:string;fingerprint:string}
type Editor={dirty:boolean;readonly revisionHash:string|null;save:()=>Promise<any>;unmount:()=>void;getMetadata:()=>any;getText:()=>Promise<string>;getNotesText:()=>Promise<string>;ensureDatabase:()=>string;importActions:(actions:any[])=>unknown;addAction:(input:any,id?:string)=>{rowId:string};updateAction:(id:string,patch:any,databaseId:string)=>unknown};
export type NativeNotesProjection={status:'loading'|'unavailable';pageId?:string}|{status:'ready';pageId?:string;fullText:string;text:string;revisionHash:string|null};
const cache=new Map<string,NativeAction[]>();
const notesCache=new Map<string,NativeNotesProjection>();
const operations=new Map<string,Promise<unknown>>();
let identityScope='',scopeGeneration=0;
let allowedProjects:Set<string>|null=null;
const notify=()=>{if(typeof window!=='undefined')window.dispatchEvent(new Event('travaux:native-actions'));};
/** Never reuse an in-memory page projection in another account or after revocation. */
export function scopeNativeActions(scope:string,projectIds?:string[]){
 if(identityScope!==scope){identityScope=scope;scopeGeneration++;cache.clear();notesCache.clear();allowedProjects=null;}
 if(projectIds){const allowed=new Set(projectIds);allowedProjects=allowed;for(const id of cache.keys())if(!allowed.has(id))cache.delete(id);for(const id of notesCache.keys())if(!allowed.has(id))notesCache.delete(id);}
}
export function nativeAccessGuard(projectId:string){const generation=scopeGeneration;return()=>{if(generation!==scopeGeneration||(allowedProjects&&!allowedProjects.has(projectId)))throw Error('L’accès actif a changé. Rouvrez le dossier dans votre session actuelle.');};}
function projectRows(editor:Editor,projectId:string):NativeAction[]{
 const metadata=editor.getMetadata();const database=metadata.databases.find((item:any)=>item.id===metadata.managedActionDatabaseId)||metadata.databases.find((item:any)=>item.id===metadata.activeDatabaseId);
 if(!database)return [];
 return database.rows.map((row:any)=>{
  const read=(name:string,type?:string)=>row.fields.find((field:any)=>field.name===name||(type&&field.type===type))?.text||'';
  const source=row.sourceUrl?.match(/^#\/mail\/([^/]+)$/)?.[1];
  const progress=read('Avancement');
  return {id:row.id,projectId,databaseId:database.id,title:read('Intitulé','title'),description:read('Description'),status:read('Statut'),owner:read('Responsable'),start:read('Début'),due:read('Échéance'),...(/^(?:100|[1-9]?\d)$/.test(progress)?{progress:Number(progress)}:{}),priority:read('Priorité'),...(source?{source}:{}),fingerprint:JSON.stringify(row.fields)};
 });
}
async function withEditor<T>(api:any,projectId:string,canWrite:boolean,run:(editor:Editor,page:{id:string})=>Promise<T>,isCurrent?:()=>boolean,existingPage?:NativeReadPage):Promise<T>{
 const scopeGuard=nativeAccessGuard(projectId);
 const guard=()=>{scopeGuard();if(isCurrent&&!isCurrent())throw Error('L’accès actif a changé. Rouvrez le dossier dans votre session actuelle.');};
 guard();
 const host=document.createElement('div');host.style.cssText='position:fixed;left:-20000px;top:0;width:1000px;height:700px;visibility:hidden;pointer-events:none;';host.inert=true;host.setAttribute('aria-hidden','true');document.body.append(host);
 let editor:Editor|undefined;
 try{
  const [project,page]=await Promise.all([api.project(projectId),existingPage?Promise.resolve(existingPage):api.nativePage(projectId)]);
  guard();
  const endpoint='/native/editor.js';const native=await import(/* @vite-ignore */endpoint);
  guard();
  editor=await native.mount(host,{pageId:page.id,title:project.name,beforeSave:guard});
  guard();
  if(canWrite){const imports=actionInputs(project.actions||[]);for(let offset=0;offset<imports.length;offset+=100)editor!.importActions(imports.slice(offset,offset+100));}
  guard();
  const result=await run(editor!,page);
  guard();
  if(canWrite)while(editor!.dirty){guard();await editor!.save();guard();}
  let projection:NativeNotesProjection;
  try{
   const fullText=await editor!.getText();guard();
   const text=await editor!.getNotesText();guard();
   projection={status:'ready',pageId:page.id,fullText,text,revisionHash:editor!.revisionHash};
  }catch{guard();projection={status:'unavailable',pageId:page.id};}
  guard();notesCache.set(projectId,projection);
  cache.set(projectId,projectRows(editor!,projectId));notify();return result;
 }finally{editor?.unmount();host.remove();}
}
function serial<T>(id:string,run:()=>Promise<T>):Promise<T>{const generation=scopeGeneration;const previous=operations.get(id)||Promise.resolve();const next=previous.catch(()=>{}).then(()=>{if(generation!==scopeGeneration)throw Error('La session active a changé. Rouvrez le dossier.');return run();});operations.set(id,next);void next.finally(()=>{if(operations.get(id)===next)operations.delete(id);}).catch(()=>{});return next;}
export function cachedNativeActions(projectIds:string[]){return projectIds.flatMap(id=>cache.get(id)||[]);}
export function cachedNativeNotes(projectId:string):NativeNotesProjection{return notesCache.get(projectId)||{status:'loading'};}
export async function loadNativeActions(api:any,projectIds:string[],canWrite:boolean,confirmedProjectIds?:string[]){
 const ids=[...new Set(projectIds)];if(!ids.length)return [];
 const guards=ids.map(nativeAccessGuard),guard=()=>guards.forEach(check=>check());guard();
 if(typeof api.pages!=='function')throw Error('La lecture des pages n’est pas disponible. Actualisez l’application.');
 const pages=await api.pages();guard();
 let confirmed=confirmedProjectIds;
 const failures:unknown[]=[];
 if(confirmed===undefined){
  confirmed=[];
  for(let offset=0;offset<ids.length;offset+=6){
   const details=await Promise.allSettled(ids.slice(offset,offset+6).map(async id=>({id,project:await api.project(id)})));guard();
   for(const result of details){if(result.status==='rejected')failures.push(result.reason);else if(actionInputs((result.value.project.actions||[]).filter((action:any)=>action.status==='accepted')).length)confirmed.push(result.value.id);}
  }
 }
 const plan=nativeReadPlan(ids,pages,confirmed,canWrite);guard();
 for(const {projectId,page}of plan.empty){cache.set(projectId,[]);if(page?.state_base64){if(!notesCache.has(projectId))notesCache.set(projectId,{status:'unavailable',pageId:page.id});}else notesCache.set(projectId,{status:'ready',...(page?{pageId:page.id}:{}),fullText:'',text:'',revisionHash:null});}
 if(plan.empty.length)notify();
 await Promise.all(Array.from({length:Math.min(2,plan.load.length)},async(_,index)=>{
  for(let offset=index;offset<plan.load.length;offset+=2){const entry=plan.load[offset];try{guard();await serial(entry.projectId,()=>withEditor(api,entry.projectId,canWrite,async()=>undefined,undefined,entry.page));}catch(failure){failures.push(failure);}}
 }));guard();
 if(failures.length)throw Error('Certaines actions n’ont pas pu être chargées. Les éléments disponibles restent affichés. Réessayez.');
 return cachedNativeActions(projectIds);
}
export async function changeNativeAction(api:any,action:NativeAction,patch:Record<string,string|number>){
 return serial(action.projectId,()=>withEditor(api,action.projectId,true,async editor=>{
  const current=projectRows(editor,action.projectId).find(row=>row.id===action.id);
  if(!current)throw new Error('Cette action a été supprimée. Actualisez la liste.');
  if(current.fingerprint!==action.fingerprint)throw new Error('Cette action a changé dans un autre écran. Actualisez la liste avant de modifier ses champs.');
  editor.updateAction(action.id,patch,current.databaseId);
 }));
}
export async function createNativeAction(api:any,projectId:string,input:Record<string,string|number>){return serial(projectId,()=>withEditor(api,projectId,true,async editor=>editor.addAction(input,editor.ensureDatabase())));}
export async function ensureFieldReportAction(api:any,report:FieldReportActionSource,dueDate:string,isCurrent?:()=>boolean){
 const input=fieldReportAction(report,dueDate);
 return serial(report.project_id,()=>withEditor(api,report.project_id,true,async(editor,page)=>{
  const result=editor.importActions([input]);
  return fieldReportLink(input.sourceKey,result,editor.getMetadata(),page.id);
 },isCurrent));
}
export async function flushNativeActions(){while(operations.size)await Promise.all([...operations.values()]);}
