import {createContext,useCallback,useContext,useEffect,useMemo,useRef,useState,type ReactNode} from 'react';
import {useSuspenseQuery,useQueryClient} from '@tanstack/react-query';
import {api,commissionWorkspaceOptions} from './data';
import {emptyWorkspace,projectFromApi,type Project,type Workspace} from './model';
import {workspaceIdentity,workspaceIdentityEvent,workspaceAccessEvent,workspaceProjectSet} from './workspace-scope.mjs';
import {Button} from '@/components/ui/button';
import {preservePanels} from './panel-lifecycle';
import {authorizedCommissions,changeWorkProfile,resolveWorkProfile,workProfilePreferenceKey,type WorkProfile,type WorkCommission,type WorkProfileSnapshot} from './work-profile-model.mjs';
export interface CreateProjectPayload{reference?:string;ref?:string;name?:string;title?:string;description?:string;location?:string;contractor?:string;delivery_date?:string;owner?:string;commission_id?:string;specialization?:string;visibility?:string}
export interface WorkspaceContext{state:Workspace;saving:boolean;refresh:()=>Promise<void>;api:any;session:any;bootstrap:any;toggleFavorite:(id:string)=>void;createProject:(payload:CreateProjectPayload)=>Promise<Project>;activeCommissionId:string;setActiveCommissionId:(id:string)=>Promise<void>;activeCommission:WorkCommission|null;commissions:WorkCommission[];workProfile:WorkProfile;workProfileLoading:boolean;workProfileNotice:string}
const Context=createContext<WorkspaceContext|null>(null);
const favoritePrefix='travaux:favorite-projects:';
function readWorkProfile(key:string|null):string|null{try{return key&&typeof window!=='undefined'?window.localStorage.getItem(key):null;}catch{return null;}}
function saveWorkProfile(key:string|null,id:string){try{if(key)window.localStorage.setItem(key,id);}catch{/* Optional navigation preference only. */}}
function readFavorites(key:string,fallback:string[]=[]):Set<string>{try{if(typeof window==='undefined')return new Set();const saved=window.localStorage.getItem(key);if(saved===null)return new Set(fallback);const raw=JSON.parse(saved);return new Set(Array.isArray(raw)?raw.filter((value:unknown)=>typeof value==='string').slice(0,1000):[]);}catch{return new Set();}}
export function WorkspaceProvider({children}:{children:ReactNode}){
 const[activeCommissionId,updateActiveCommissionId]=useState('all');
 const currentOptions=useMemo(()=>commissionWorkspaceOptions(activeCommissionId),[activeCommissionId]);
 const{data}=useSuspenseQuery(currentOptions);const client=useQueryClient();const[pending,setPending]=useState(0);
 const[observedIdentity,setObservedIdentity]=useState(()=>workspaceIdentity(data.session));
 const identityRef=useRef(observedIdentity);
 const profileKey=workProfilePreferenceKey(data.session);
 const[profilePreference,setProfilePreference]=useState<{key:string|null;id:string|null}>({key:null,id:null});
 const[profileNotice,setProfileNotice]=useState<{key:string|null;text:string}|null>(null);
 const savedProfile=profilePreference.key===profileKey?profilePreference.id:readWorkProfile(profileKey);
 const commissions=useMemo(()=>authorizedCommissions(data.bootstrap),[data.bootstrap]);
 const workProfile=resolveWorkProfile(data.session,data.bootstrap,savedProfile,data.state.projects.length>0);
 const profileSnapshot=useRef<WorkProfileSnapshot>({identity:observedIdentity,session:data.session,bootstrap:data.bootstrap,hasProjects:data.state.projects.length>0});
 profileSnapshot.current={identity:identityRef.current,session:data.session,bootstrap:data.bootstrap,hasProjects:data.state.projects.length>0};
 useEffect(()=>{
  if(workProfile.status==='inactive')return;
  if(workProfile.status==='ready'&&workProfile.commissionId){
   const id=workProfile.commissionId;
   if(workProfile.changed)setProfileNotice({key:profileKey,text:'Vos accès ont changé. Un profil encore autorisé a été sélectionné.'});
   setProfilePreference(previous=>previous.key===profileKey&&previous.id===id?previous:{key:profileKey,id});
   saveWorkProfile(profileKey,id);updateActiveCommissionId(id);
  }else if(activeCommissionId!=='all')updateActiveCommissionId('all');
 },[profileKey,workProfile.status,workProfile.commissionId,workProfile.changed,activeCommissionId]);
 const[observedAccess,setObservedAccess]=useState(()=>({key:workspaceIdentity(data.session),projects:workspaceProjectSet(data.state.projects.map(project=>project.id))}));
 useEffect(()=>{const changed=(event:Event)=>{if(!(event instanceof CustomEvent)||typeof event.detail?.key!=='string')return;identityRef.current=event.detail.key;setObservedIdentity(event.detail.key);const stored=client.getQueryData<import('./data').WorkspaceData>(currentOptions.queryKey);if(stored&&workspaceIdentity(stored.session)!==event.detail.key){updateActiveCommissionId('all');client.setQueriesData({queryKey:['workspace','fastapi-v1']},{state:emptyWorkspace(),session:null,bootstrap:null});}};window.addEventListener(workspaceIdentityEvent,changed);return()=>window.removeEventListener(workspaceIdentityEvent,changed);},[client,currentOptions.queryKey]);
 useEffect(()=>{const changed=(event:Event)=>{if(event instanceof CustomEvent&&typeof event.detail?.key==='string'&&typeof event.detail?.projects==='string')setObservedAccess(event.detail);};window.addEventListener(workspaceAccessEvent,changed);return()=>window.removeEventListener(workspaceAccessEvent,changed);},[]);
 const switchCommission=useCallback(async(id:string)=>{await changeWorkProfile({commissionId:id,snapshot:()=>({...profileSnapshot.current,identity:identityRef.current}),preserve:preservePanels,commit:selected=>{const key=workProfilePreferenceKey(profileSnapshot.current.session);setProfilePreference({key,id:selected});saveWorkProfile(key,selected);setProfileNotice(null);updateActiveCommissionId(selected);}});},[]);
 const activeCommission=useMemo(()=>commissions.find(item=>item.id===activeCommissionId)||null,[commissions,activeCommissionId]);
 const preferenceKey=favoritePrefix+encodeURIComponent(String(data.session?.actor?.tenant_id||'anonymous'))+':'+encodeURIComponent(String(data.session?.actor?.actor_id||'anonymous'));
 const[favorites,setFavorites]=useState(()=>({key:preferenceKey,ids:readFavorites(preferenceKey,data.state.projects.filter(project=>project.favorite).map(project=>project.id))}));
 useEffect(()=>{setFavorites(previous=>previous.key===preferenceKey?previous:{key:preferenceKey,ids:readFavorites(preferenceKey,data.state.projects.filter(project=>project.favorite).map(project=>project.id))});},[preferenceKey]);
 useEffect(()=>{if(favorites.key!==preferenceKey)return;try{window.localStorage.setItem(preferenceKey,JSON.stringify([...favorites.ids]));}catch{/* Optional UI preference only. */}},[favorites,preferenceKey]);
 const state=useMemo<Workspace>(()=>({...data.state,projects:data.state.projects.map(project=>({...project,favorite:favorites.key===preferenceKey&&favorites.ids.has(project.id)}))}),[data.state,favorites,preferenceKey]);
 const refresh=useCallback(async()=>{await client.fetchQuery({...currentOptions,staleTime:0});},[client,currentOptions]);
 const toggleFavorite=useCallback((id:string)=>{if(!data.state.projects.some(project=>project.id===id))return;setFavorites(previous=>{const ids=new Set(previous.key===preferenceKey?previous.ids:readFavorites(preferenceKey,data.state.projects.filter(project=>project.favorite).map(project=>project.id)));if(ids.has(id))ids.delete(id);else ids.add(id);return{key:preferenceKey,ids};});},[data.state.projects,preferenceKey]);
 const createProject=useCallback(async(payload:CreateProjectPayload)=>{setPending(count=>count+1);try{const created=await api.createProject({reference:String(payload.reference||payload.ref||'').trim(),name:String(payload.name||payload.title||'').trim(),description:String(payload.description||'').trim(),location:String(payload.location||'').trim(),contractor:String(payload.contractor||'').trim(),delivery_date:String(payload.delivery_date||'').trim(),owner:String(payload.owner||'').trim(),commission_id:payload.commission_id||(activeCommissionId!=='all'?activeCommissionId:undefined),specialization:payload.specialization||undefined,visibility:payload.visibility||'public'});await refresh();return projectFromApi(created);}finally{setPending(count=>Math.max(0,count-1));}},[refresh,activeCommissionId]);
 if(observedIdentity!==workspaceIdentity(data.session))return <main className="content auth-gate"><h1>Ouverture de votre espace</h1><p>Le compte actif a changé. Son espace doit être chargé avant de poursuivre.</p><Button onClick={()=>{void refresh().catch(()=>{});}}>Recharger l’espace</Button></main>;
 const accessPending=activeCommissionId==='all'&&observedAccess.key===workspaceIdentity(data.session)&&observedAccess.projects!==workspaceProjectSet(data.state.projects.map(project=>project.id));
 return <Context.Provider value={{state,saving:pending>0,refresh,api,session:data.session,bootstrap:data.bootstrap,toggleFavorite,createProject,activeCommissionId,setActiveCommissionId:switchCommission,activeCommission,commissions,workProfile,workProfileLoading:workProfile.status==='ready'&&activeCommissionId!==workProfile.commissionId,workProfileNotice:profileNotice?.key===profileKey?profileNotice.text:''}}><div hidden={accessPending} inert={accessPending}>{children}</div>{accessPending&&<main className="content auth-gate"><h1>Actualisation de vos accès</h1><p>La liste de vos dossiers a changé. Rechargez votre espace pour poursuivre.</p><Button onClick={()=>{void refresh().catch(()=>{});}}>Recharger l’espace</Button></main>}</Context.Provider>;
}
export function useWorkspace():WorkspaceContext{const context=useContext(Context);if(!context)throw new Error('Espace non chargé');return context;}
