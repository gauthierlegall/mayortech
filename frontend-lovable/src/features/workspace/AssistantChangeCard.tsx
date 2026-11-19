import {useCallback,useEffect,useRef,useState} from 'react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {preservePanels} from './panel-lifecycle';
import {assistantProposal,canRequestChange,proposalPresentation} from './assistant-change-model.mjs';
import './assistant-change.css';

type Proposal=ReturnType<typeof assistantProposal>;
export function AssistantChangeCard({id,projectId,conversationId,onApplied,autoReveal=false}:{id:string;projectId:string;conversationId:string;onApplied:(proposal:Proposal)=>Promise<void>;autoReveal?:boolean}){
 const {api,state,bootstrap}=useWorkspace();
 const [proposal,setProposal]=useState<Proposal|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[mustReload,setMustReload]=useState(false),[refreshed,setRefreshed]=useState(false);
 const alive=useRef(true),working=useRef(false),loadEpoch=useRef(0),appliedRef=useRef(onApplied),root=useRef<HTMLElement>(null);appliedRef.current=onApplied;
 const binding={id,projectId,conversationId};
 const load=useCallback(async()=>{
  if(working.current)return;working.current=true;setBusy(true);setError('');const epoch=++loadEpoch.current;
  try{
   const next=assistantProposal(await api.assistantChange(id),{id,projectId,conversationId});
   if(!alive.current||epoch!==loadEpoch.current)return;
   setProposal(next);setMustReload(true);
   if(next.status==='applied')await appliedRef.current(next);
   if(alive.current&&epoch===loadEpoch.current){setRefreshed(next.status==='applied');setMustReload(false);}
  }catch(cause){if(alive.current&&epoch===loadEpoch.current){setError(cause instanceof Error?cause.message:'La proposition ne peut pas être chargée. Réessayez.');setMustReload(true);}}
  finally{working.current=false;if(alive.current&&epoch===loadEpoch.current)setBusy(false);}
 },[api,id,projectId,conversationId]);
 useEffect(()=>{alive.current=true;setProposal(null);setRefreshed(false);void load();return()=>{alive.current=false;loadEpoch.current++;};},[load]);
 useEffect(()=>{if(proposal&&autoReveal){const frame=requestAnimationFrame(()=>root.current?.scrollIntoView({block:'nearest'}));return()=>cancelAnimationFrame(frame);}},[proposal?.id,autoReveal]);
 async function decide(action:'confirm'|'reject'){
  if(!proposal||proposal.status!=='pending'||working.current||mustReload||!canRequestChange(bootstrap,projectId))return;
  working.current=true;setBusy(true);setError('');
  try{
   if(action==='confirm')await preservePanels();
   const raw=action==='confirm'?await api.confirmAssistantChange(id,proposal.plan_hash):await api.rejectAssistantChange(id);
   const next=assistantProposal(raw,binding);
   if(next.plan_hash!==proposal.plan_hash||next.status!==(action==='confirm'?'applied':'rejected'))throw Error('La confirmation reçue ne correspond pas à la proposition relue. Actualisez son état avant toute autre action.');
   if(!alive.current)return;
   setProposal(next);setMustReload(true);
   if(next.status==='applied')await appliedRef.current(next);
   if(alive.current){setRefreshed(next.status==='applied');setMustReload(false);}
  }catch(cause){if(alive.current){setError(cause instanceof Error?cause.message:'La décision n’a pas pu être vérifiée. Actualisez la proposition.');setMustReload(true);}}
  finally{working.current=false;if(alive.current)setBusy(false);}
 }
 const presentation=proposal?proposalPresentation(proposal):null,expired=proposal?.status==='pending'&&proposal.expires_at*1000<=Date.now();
 const canWrite=canRequestChange(bootstrap,projectId),project=state.projects.find(item=>item.id===projectId);
 return <section ref={root} className="assistant-change" aria-label="Modification proposée" aria-busy={busy}>
  <h3>{proposal?.status==='applied'&&refreshed?'Modification appliquée':proposal?.status==='rejected'?'Proposition abandonnée':'Modification proposée'}</h3>
  <p className="assistant-change-project">Dossier : {project?.title||'Dossier sélectionné'}</p>
  {presentation&&<dl><dt>{presentation.label}</dt><dd>{presentation.value}</dd></dl>}
  {!proposal&&busy&&<p role="status">Chargement de la proposition…</p>}
  {error&&<p role="alert">{error}</p>}
  {proposal?.status==='applied'&&!refreshed&&<p role="status">La confirmation a été reçue. Actualisez le dossier pour vérifier son nouvel état.</p>}
  {expired&&<p>Cette proposition a expiré. Envoyez une nouvelle demande pour préparer une modification actuelle.</p>}
  {proposal?.status==='pending'&&!expired&&<p>Relisez cette valeur. La confirmation l’ajoutera au dossier avec la trace de votre décision.</p>}
  {proposal?.status==='pending'&&canWrite&&!mustReload&&<div className="assistant-change-actions"><Button size="sm" disabled={busy||expired} onClick={()=>void decide('confirm')}>{busy?'Vérification…':'Confirmer la modification'}</Button><Button variant="ghost" size="sm" disabled={busy} onClick={()=>void decide('reject')}>Abandonner</Button></div>}
  {proposal?.status==='pending'&&!canWrite&&<p>Votre accès permet de lire cette proposition. Sa confirmation nécessite un droit de modification sur le dossier.</p>}
  {(mustReload||!proposal)&&!busy&&<Button variant="outline" size="sm" onClick={()=>void load()}>Actualiser la proposition</Button>}
 </section>;
}
