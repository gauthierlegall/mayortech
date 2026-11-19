import {useCallback,useEffect,useRef,useState} from 'react';
import {RefreshCw} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {canReviewOrganizationRequests,decideOrganizationRequest,organizationRequestsCatalog} from './organization-requests-model.mjs';
import './organization-join.css';

interface JoinRequest {actor_id:string;display_name:string;email:string;status:'pending'|'joined'|'rejected';revision:number;requested_at:string}
const message=(failure:unknown)=>failure instanceof Error?failure.message:'Les demandes ne peuvent pas être chargées. Réessayez.';
const date=(value:string)=>new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value));

export function OrganizationRequests({onChanged}:{onChanged:()=>void}){
 const {session,bootstrap}=useWorkspace();
 if(!canReviewOrganizationRequests(session,bootstrap))return null;
 return <RequestList key={JSON.stringify([session?.actor?.tenant_id,session?.actor?.actor_id,bootstrap?.role,bootstrap?.permissions?.organization?.write])} onChanged={onChanged}/>;
}
function RequestList({onChanged}:{onChanged:()=>void}){
 const {api,session,bootstrap}=useWorkspace();
 const [items,setItems]=useState<JoinRequest[]|null>(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(''),[error,setError]=useState(''),[rowError,setRowError]=useState<{id:string;message:string}|null>(null),[stale,setStale]=useState(''),[denied,setDenied]=useState(false);
 const alive=useRef(true),epoch=useRef(0),working=useRef(false);
 const guard=()=>{if(!alive.current)throw Error('Le compte ou l’organisation active a changé.');};
 const load=useCallback(async()=>{
  if(working.current)return;const token=++epoch.current;setLoading(true);setError('');
  try{const catalog=organizationRequestsCatalog(await api.organizationJoinRequests());if(alive.current&&epoch.current===token){setItems(catalog.items);setStale('');setRowError(null);setDenied(false);}}
  catch(failure){if(alive.current&&epoch.current===token){setItems(null);setError(message(failure));setDenied((failure as any)?.status===403);}}
  finally{if(alive.current&&epoch.current===token)setLoading(false);}
 },[api]);
 useEffect(()=>{alive.current=true;void load();return()=>{alive.current=false;epoch.current++;};},[load]);
 async function decide(request:JoinRequest,decision:'approve'|'reject'){
  if(working.current||loading||stale||denied)return;
  working.current=true;setBusy(request.actor_id);setRowError(null);
  try{
   const result=await decideOrganizationRequest({api,request,decision,session,bootstrap,assertCurrent:guard});guard();
   setItems(previous=>previous?.map(item=>item.actor_id===request.actor_id?{...item,status:result.status as 'joined'|'rejected'}:item)??null);
   onChanged();
  }catch(failure){if(alive.current){const conflict=(failure as any)?.status===409;setRowError({id:request.actor_id,message:conflict?'Cette demande a changé depuis son affichage. Actualisez la liste avant de décider.':message(failure)});if(conflict)setStale(request.actor_id);if((failure as any)?.status===403){setDenied(true);setItems(null);setError('Votre accès administrateur ne permet plus de traiter ces demandes.');}}}
  finally{working.current=false;if(alive.current)setBusy('');}
 }
 return <section className="organization-access-requests" aria-labelledby="organization-requests-title" aria-busy={loading||Boolean(busy)}>
  <div className="access-heading"><div><h2 id="organization-requests-title">Demandes d’accès</h2><p>Acceptez ou refusez les demandes envoyées avec le code de votre organisation.</p></div><Button variant="outline" size="sm" disabled={loading||Boolean(busy)} onClick={()=>void load()}><RefreshCw size={15}/>Actualiser les demandes</Button></div>
  {loading&&!items&&<p role="status">Chargement des demandes…</p>}
  {error&&<p className="form-error" role="alert">{error}</p>}
  {items&&items.length===0&&<p>Aucune demande d’accès pour le moment.</p>}
  {items&&items.length>0&&<ul className="organization-request-list">{items.map(request=><li key={request.actor_id} className="organization-request-row"><div><h3>{request.display_name}</h3>{request.email&&<p>{request.email}</p>}<time dateTime={request.requested_at}>Demande du {date(request.requested_at)}</time></div>{request.status==='pending'?<div className="organization-request-actions"><Button disabled={Boolean(busy)||loading||Boolean(stale)||denied} onClick={()=>void decide(request,'approve')}>{busy===request.actor_id?'Traitement…':'Accepter'}<span className="sr-only"> la demande de {request.display_name}</span></Button><Button variant="outline" disabled={Boolean(busy)||loading||Boolean(stale)||denied} onClick={()=>void decide(request,'reject')}>Refuser<span className="sr-only"> la demande de {request.display_name}</span></Button></div>:<p role="status" className="organization-request-status">{request.status==='joined'?'Demande acceptée. Accès lecteur autorisé ; les dossiers sont attribués dans Rôles et droits.':'Demande refusée.'}</p>}{rowError?.id===request.actor_id&&<p className="form-error" role="alert">{rowError.message}</p>}</li>)}</ul>}
 </section>;
}
