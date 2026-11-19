import React,{Suspense,useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {WorkspaceProvider,useWorkspace} from '../../../src/features/workspace/context';
import {workspaceOptions} from '../../../src/features/workspace/data';
import {control} from './workspace-api-mock';

const queryClient=new QueryClient({defaultOptions:{queries:{retry:false,refetchOnWindowFocus:false}}});
(window as any).lab={diagnostics:()=>({phase:'preloading',requests:control.requests})};
await queryClient.fetchQuery(workspaceOptions);
function PrivateContent(){const {state,session}=useWorkspace();const[draft,setDraft]=useState('');useEffect(()=>{(window as any).__privateMounts=((window as any).__privateMounts||0)+1;},[]);return <section aria-label="Contenu métier protégé"><h2>{state.organization}</h2><p>Ancienne identité des données : {session.actor.actor_id}</p>{state.projects.map(project=><h3 key={project.id}>{project.title}</h3>)}{control.grantsScenario&&<label>Note fictive du dossier conservé<textarea aria-label="Note fictive du dossier conservé" value={draft} onChange={event=>setDraft(event.target.value)}/></label>}</section>;}
(window as any).lab={
 async refreshAfterCookieSwitch(){
  control.actor='account-b';let failed=false;
  try{await queryClient.fetchQuery({...workspaceOptions,staleTime:0,retry:false});}catch{failed=true;}
  const cached=queryClient.getQueryData<any>(workspaceOptions.queryKey);
  return {failed,cachedActor:cached?.session?.actor?.actor_id??null,cachedProjects:cached?.state?.projects?.map((project:any)=>project.id)??null,requests:control.requests};
 },
 async refreshAfterGrantRemoval(){control.allowed=['retained'];control.failDetails=true;let failed=false;try{await queryClient.fetchQuery({...workspaceOptions,staleTime:0,retry:false});}catch{failed=true;}const cached=queryClient.getQueryData<any>(workspaceOptions.queryKey);return {failed,cachedProjects:cached?.state?.projects?.map((project:any)=>project.id),requests:control.requests,mounts:(window as any).__privateMounts};},
 async retryGrantedLoad(){control.failDetails=false;await queryClient.fetchQuery({...workspaceOptions,staleTime:0,retry:false});return {mounts:(window as any).__privateMounts};},
 diagnostics(){const cached=queryClient.getQueryData<any>(workspaceOptions.queryKey);return {cachedActor:cached?.session?.actor?.actor_id,requests:control.requests};},
};
createRoot(document.getElementById('root')!).render(<QueryClientProvider client={queryClient}><main><h1>Recette React — transport API simulé</h1><p className="notice">Vrais WorkspaceProvider, QueryClient et loadWorkspace. Seule l’API est contrôlée ; aucun compte ni serveur métier réel.</p><Suspense fallback={<p>Ouverture de la fixture…</p>}><WorkspaceProvider><PrivateContent/></WorkspaceProvider></Suspense></main></QueryClientProvider>);
