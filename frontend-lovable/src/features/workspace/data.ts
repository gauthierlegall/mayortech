import {queryOptions} from '@tanstack/react-query';
import {api as sharedApi} from '../../../../web/api.js';
import {requiresOrganization} from './organization-join-model.mjs';
import {scopeNativeActions} from './native-actions';
import {observeWorkspaceIdentity,observeWorkspaceAccess} from './workspace-scope.mjs';
import {commissionRequestFilter} from './work-profile-model.mjs';
import {confirmedActionsFromApi,documentFromApi,emptyWorkspace,historyFromApi,list,messageFromApi,projectFromApi,text,type Workspace} from './model';
export const api:any=sharedApi;
export interface WorkspaceData{state:Workspace;session:any;bootstrap:any}
async function mapBatched<T,R>(items:T[],run:(item:T)=>Promise<R>):Promise<R[]>{const output:R[]=[];for(let offset=0;offset<items.length;offset+=6)output.push(...await Promise.all(items.slice(offset,offset+6).map(run)));return output;}
export async function loadWorkspace(client:any=api,commissionId:string='all'):Promise<WorkspaceData>{
 const session=await client.session(),identity=observeWorkspaceIdentity(session);scopeNativeActions(identity);if(!session?.authenticated||requiresOrganization(session)){scopeNativeActions(identity,[]);return{state:emptyWorkspace(),session,bootstrap:null};}
 const bootstrap=await client.bootstrap();
 // A removed commission grant must allow a safe return to the authorized dossier list.
 const projectRows=await client.projects(commissionRequestFilter(bootstrap,commissionId));const permitted=(resource:string,action='read')=>bootstrap?.permissions?.[resource]?.[action]!==false;
 scopeNativeActions(identity,list(projectRows).map(row=>text(row.id)));
 if(commissionId==='all')observeWorkspaceAccess(identity,list(projectRows).map(row=>text(row.id)));
 const [projects,mailbox,summaries,organization,members,audit]=await Promise.all([
  mapBatched(list(projectRows),async(base:any)=>{const[detail,documents]=await Promise.all([client.project(base.id),client.documents(base.id)]);return{base,detail,documents:list(documents)};}),
  permitted('mail')?client.mailboxMessages({folder:'all',limit:200,offset:0}):{items:[],total:0},client.summaries(),
  permitted('organization')?client.organization():null,permitted('members')?client.organizationMembers():{items:[]},permitted('audit')?client.organizationAudit():null,
 ]);
 const state=emptyWorkspace();state.projects=projects.map(({base,detail})=>projectFromApi(base,detail)).sort((a,b)=>Number(b.storyline)-Number(a.storyline)||(a.storyline&&b.storyline?['TRV-2026-042','TRV-2026-038','TRV-2026-045','TRV-2026-031'].indexOf(a.ref)-['TRV-2026-042','TRV-2026-038','TRV-2026-045','TRV-2026-031'].indexOf(b.ref):0)||b.pendingCount-a.pendingCount||Number(b.status==='En cours')-Number(a.status==='En cours')||b.updatedAt.localeCompare(a.updatedAt));state.actions=projects.flatMap(({base,detail})=>confirmedActionsFromApi(detail,text(base.id)));
 state.documents=projects.flatMap(({base,documents})=>documents.filter(row=>row.kind==='attachment').map(row=>documentFromApi(row,text(base.id))));
 const attachmentByMail=new Map<string,string>();for(const document of state.documents)if(document.parentSourceId&&!attachmentByMail.has(document.parentSourceId))attachmentByMail.set(document.parentSourceId,document.id);
 state.messages=list(mailbox).map(row=>messageFromApi(row,attachmentByMail.get(text(row.id))));state.messageTotal=Number.isFinite(mailbox?.total)?mailbox.total:state.messages.length;state.messagesComplete=state.messageTotal<=state.messages.length;
 state.history=audit?list(audit).map(row=>historyFromApi(row)):projects.flatMap(({base,detail})=>list(detail?.events).map(row=>historyFromApi(row,text(base.id))));
 state.summaries=list(summaries).map(row=>({id:text(row.id),projectId:text(row.project_id),date:text(row.created_at),text:text(row.content),source:text(row.project_id),status:text(row.status),stale:row.stale===true,coverage:text(row.coverage)}));state.organization=text(organization?.name);
 state.members=list(members).map(row=>({id:text(row.id),name:text(row.display_name),service:text(row.service),role:text(row.role_label),active:row.is_current===true}));
 for(const{base,detail}of projects)state.notes[text(base.id)]=list(detail?.notes).map(note=>text(note.content)||text(note.body)).filter(Boolean).join('\n\n');
 return{state,session,bootstrap};
}
export function commissionWorkspaceOptions(commissionId:string='all'){
 return queryOptions({queryKey:['workspace','fastapi-v1',commissionId||'all'],queryFn:()=>loadWorkspace(api,commissionId||'all'),staleTime:0,retry:false,refetchOnWindowFocus:false});
}
export const workspaceOptions=commissionWorkspaceOptions('all');
