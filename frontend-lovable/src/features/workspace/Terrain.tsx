import {useEffect,useRef,useState} from 'react';
import {Link} from '@tanstack/react-router';
import {ClipboardCheck,Plus,Check,ArrowRight,RefreshCw} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '@/components/ui/dialog';
import {useWorkspace} from './context';
import {formatDate} from './model';
import {cachedNativeActions,ensureFieldReportAction,type NativeAction} from './native-actions';
import {registerPreserver} from './panel-lifecycle';
import './terrain.css';

interface FieldReport{id:string;project_id:string;kind:'Visite'|'Anomalie'|'Réserve';date:string;title:string;detail:string;author:string;status:'À traiter'|'Levée';revision:number;source_id:string;action_link:null|{page_id:string;database_id:string;row_id:string;source_key:string}}
type Draft={project_id:string;kind:FieldReport['kind'];date:string;title:string;detail:string;author:string};
const errorText=(failure:unknown)=>failure instanceof Error?failure.message:'Le constat n’a pas pu être enregistré. Réessayez.';

export function Terrain(props:{projectId?:string}){
 const {session}=useWorkspace();
 const identity=JSON.stringify([session?.authenticated===true,session?.actor?.tenant_id||'',session?.actor?.actor_id||'',props.projectId||'']);
 const currentIdentity=useRef(identity);currentIdentity.current=identity;
 return <TerrainSession key={identity} {...props} isCurrentContext={()=>currentIdentity.current===identity}/>;
}
function TerrainSession({projectId,isCurrentContext}:{projectId?:string;isCurrentContext:()=>boolean}){
 const {state,api,bootstrap,session,refresh}=useWorkspace();
 const [create,setCreate]=useState(false),[filter,setFilter]=useState(projectId??'all'),[status,setStatus]=useState('all'),[selected,setSelected]=useState<FieldReport|null>(null),[reports,setReports]=useState<FieldReport[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[createError,setCreateError]=useState(''),[actionError,setActionError]=useState(''),[busy,setBusy]=useState(''),[retry,setRetry]=useState(0),[draft,setDraft]=useState<Draft|null>(null),[actionDue,setActionDue]=useState(''),[total,setTotal]=useState(0),[nativeRows,setNativeRows]=useState<NativeAction[]>([]);
 const alive=useRef(true),epoch=useRef(0),pending=useRef(false),clientId=useRef('');
 const stillCurrent=(token?:number)=>alive.current&&isCurrentContext()&&(token===undefined||token===epoch.current);
 const canWrite=bootstrap?.permissions?.workspace?.write===true;
 const memberNames=[...new Set(state.members.map(member=>member.name).filter(Boolean))];
 const authors=memberNames.length?memberNames:[String(session?.actor?.display_name||session?.actor?.actor_id||'Service travaux')];
 const projectName=(id:string)=>state.projects.find(project=>project.id===id)?.title||'Chantier';
 const upsert=(record:FieldReport)=>setReports(previous=>[record,...previous.filter(item=>item.id!==record.id)].filter(item=>(projectId?item.project_id===projectId:filter==='all'||item.project_id===filter)&&(status==='all'||item.status===status)).sort((a,b)=>b.date.localeCompare(a.date)));
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;epoch.current++;};},[]);
 useEffect(()=>registerPreserver(()=>{if(pending.current)throw Error('Attendez l’enregistrement du constat avant de quitter cette page.');},()=>pending.current),[]);
 useEffect(()=>{
  const token=++epoch.current;setLoading(true);setError('');
  api.fieldReports({project_id:projectId||(filter==='all'?undefined:filter),status:status==='all'?undefined:status}).then((value:any)=>{if(stillCurrent(token)){setReports(value.items||[]);setTotal(value.total||0);}}).catch((failure:unknown)=>{if(stillCurrent(token))setError(errorText(failure));}).finally(()=>{if(stillCurrent(token))setLoading(false);});
 },[api,projectId,filter,status,retry]);
 useEffect(()=>{const changed=()=>{if(stillCurrent())setNativeRows(cachedNativeActions(state.projects.map(project=>project.id)));};changed();window.addEventListener('travaux:native-actions',changed);return()=>window.removeEventListener('travaux:native-actions',changed);},[state.projects]);
 function openCreate(){
  if(!draft){setDraft({project_id:projectId||(filter==='all'?state.projects[0]?.id||'':filter),kind:'Visite',date:new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Paris',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()),title:'',detail:'',author:authors[0]||'Service travaux'});clientId.current=crypto.randomUUID();}
  setCreateError('');setCreate(true);
 }
 async function toggle(report:FieldReport){
  if(pending.current||!stillCurrent())return;const token=epoch.current;pending.current=true;setBusy(report.id);setError('');
  try{const record=await api.updateFieldReport(report.id,{expected_revision:report.revision,status:report.status==='Levée'?'À traiter':'Levée'}) as FieldReport;if(!stillCurrent(token))return;upsert(record);void refresh().catch(()=>{});}
  catch(failure){if(stillCurrent(token))setError(errorText(failure));}
  finally{pending.current=false;if(stillCurrent())setBusy('');}
 }
 async function refreshSelected(){
  if(!selected||pending.current||!stillCurrent())return;const token=epoch.current;setActionError('');
  try{const record=await api.fieldReport(selected.id) as FieldReport;if(!stillCurrent(token))return;setSelected(record);upsert(record);}
  catch(failure){if(stillCurrent(token))setActionError(errorText(failure));}
 }
 return <section className={projectId?'terrain-section':'content terrain-section'}>
  {!projectId&&<div className="page-heading"><div><h1>Suivi terrain</h1></div></div>}
  <div className="section-heading"><h2>{projectId?'Constats du chantier':'Comptes rendus et réserves'} <span>{reports.length}</span></h2>{canWrite&&<Button size="sm" disabled={Boolean(busy)||!state.projects.length} onClick={openCreate}><Plus/>Nouveau constat</Button>}</div>
  <div className="filterbar wrap">{!projectId&&<select aria-label="Chantier des constats" value={filter} onChange={event=>setFilter(event.target.value)}><option value="all">Tous les chantiers</option>{state.projects.map(project=><option key={project.id} value={project.id}>{project.title}</option>)}</select>}<select aria-label="Statut des constats" value={status} onChange={event=>setStatus(event.target.value)}><option value="all">Tous les statuts</option><option>À traiter</option><option>Levée</option></select></div>
  {error&&<div className="terrain-error" role="alert"><p>{error}</p><Button variant="outline" size="sm" disabled={Boolean(busy)} onClick={()=>setRetry(value=>value+1)}><RefreshCw size={14}/>Actualiser les constats</Button></div>}
  {loading&&<p className="muted-label" role="status">Chargement des constats…</p>}
  {!loading&&!reports.length&&!error?<div className="terrain-empty"><ClipboardCheck size={32}/><h3>Aucun constat enregistré</h3>{canWrite&&<Button variant="outline" onClick={openCreate}><Plus/>Ajouter un constat</Button>}</div>:<div className="terrain-list">{reports.map(report=>{
   const linked=report.action_link?nativeRows.find(action=>action.id===report.action_link!.row_id&&action.projectId===report.project_id):null;
   return <article key={report.id} className="terrain-row"><div className={`overview-icon ${report.status==='Levée'?'green-tone':'amber-tone'}`}><ClipboardCheck/></div><div className="terrain-copy"><small>{report.kind} · {formatDate(report.date)} · {report.author}</small><h3>{report.title}</h3><p>{report.detail}</p><Link to="/chantiers/$id" params={{id:report.project_id}}>{projectName(report.project_id)}<ArrowRight size={12}/></Link>{report.action_link&&<a className="terrain-action-link" href={`#/chantiers/${encodeURIComponent(report.project_id)}?view=table`}>Action liée{linked?` : ${linked.status||'Statut à préciser'}`:' · Voir dans les actions'}<ArrowRight size={12}/></a>}</div><div className="terrain-controls"><span className={`status-pill ${report.status==='Levée'?'done':'waiting'}`}><span/>{report.status}</span>{canWrite&&<><Button variant="outline" size="sm" disabled={Boolean(busy)} onClick={()=>void toggle(report)}>{report.status==='Levée'?'Rouvrir':<><Check/>Lever le constat</>}</Button>{!report.action_link&&<Button variant="ghost" size="sm" disabled={Boolean(busy)} onClick={()=>{setSelected(report);setActionDue(report.date);setActionError('');}}><Plus/>Créer une action</Button>}</>}</div></article>;
  })}</div>}
  {total>reports.length&&!loading&&<p className="terrain-note">Affichage limité à {reports.length} constats sur {total}. Choisissez un chantier ou un statut pour affiner.</p>}
  <Dialog open={create} onOpenChange={open=>{if(!pending.current)setCreate(open);}}><DialogContent className="terrain-dialog"><DialogTitle>Nouveau constat terrain</DialogTitle><DialogDescription>Compte rendu de visite, anomalie ou réserve du chantier.</DialogDescription>{draft&&<form className="form-stack" onSubmit={async event=>{
   event.preventDefault();if(pending.current||!stillCurrent())return;const token=epoch.current;pending.current=true;setBusy('create');setCreateError('');
   try{const record=await api.createFieldReport({...draft,client_id:clientId.current}) as FieldReport;if(!stillCurrent(token))return;upsert(record);setCreate(false);setDraft(null);clientId.current='';setRetry(value=>value+1);void refresh().catch(()=>{});}
   catch(failure){if(stillCurrent(token))setCreateError(errorText(failure));}
   finally{pending.current=false;if(stillCurrent())setBusy('');}
  }}><label>Chantier<select value={draft.project_id} required disabled={Boolean(busy)||Boolean(projectId)} onChange={event=>setDraft({...draft,project_id:event.target.value})}>{state.projects.map(project=><option key={project.id} value={project.id}>{project.title}</option>)}</select></label><div className="form-pair"><label>Type<select aria-label="Type" value={draft.kind} disabled={Boolean(busy)} onChange={event=>setDraft({...draft,kind:event.target.value as Draft['kind']})}><option>Visite</option><option>Anomalie</option><option>Réserve</option></select></label><label>Date<input type="date" required value={draft.date} disabled={Boolean(busy)} onChange={event=>setDraft({...draft,date:event.target.value})}/></label></div><label>Titre<input required maxLength={160} value={draft.title} disabled={Boolean(busy)} onChange={event=>setDraft({...draft,title:event.target.value})}/></label><label>Constat / compte rendu<textarea required rows={5} maxLength={20000} value={draft.detail} disabled={Boolean(busy)} onChange={event=>setDraft({...draft,detail:event.target.value})}/></label><label>Auteur<select value={draft.author} disabled={Boolean(busy)} onChange={event=>setDraft({...draft,author:event.target.value})}>{authors.map(author=><option key={author}>{author}</option>)}</select></label>{createError&&<p className="form-error" role="alert">{createError} Votre saisie reste disponible.</p>}<Button type="submit" disabled={Boolean(busy)}>{busy==='create'?'Enregistrement…':'Enregistrer le constat'}</Button></form>}</DialogContent></Dialog>
  <Dialog open={Boolean(selected)} onOpenChange={open=>{if(!pending.current&&!open)setSelected(null);}}><DialogContent className="terrain-dialog"><DialogTitle>Créer une action liée</DialogTitle><DialogDescription>{selected?.title}</DialogDescription><form className="form-stack" onSubmit={async event=>{
   event.preventDefault();if(!selected||pending.current||!stillCurrent())return;const token=epoch.current;pending.current=true;setBusy('action');setActionError('');
   try{const link=await ensureFieldReportAction(api,selected,actionDue,()=>stillCurrent(token));if(!stillCurrent(token))return;const record=await api.linkFieldReportAction(selected.id,{...link,expected_revision:selected.revision}) as FieldReport;if(!stillCurrent(token))return;upsert(record);setSelected(null);void refresh().catch(()=>{});}
   catch(failure){if(stillCurrent(token))setActionError(errorText(failure));}
   finally{pending.current=false;if(stillCurrent())setBusy('');}
  }}><label>Échéance<input type="date" required value={actionDue} disabled={Boolean(busy)} onChange={event=>setActionDue(event.target.value)}/></label>{actionError&&<div className="terrain-error" role="alert"><p>{actionError}</p><Button type="button" variant="outline" size="sm" disabled={Boolean(busy)} onClick={()=>void refreshSelected()}><RefreshCw size={14}/>Actualiser le constat</Button></div>}<Button type="submit" disabled={Boolean(busy)||Boolean(selected?.action_link)}><Plus/>{busy==='action'?'Création…':'Créer l’action'}</Button></form></DialogContent></Dialog>
 </section>;
}
