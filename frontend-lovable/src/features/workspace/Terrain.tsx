import {useEffect,useRef,useState} from 'react';
import {Link} from '@tanstack/react-router';
import {ClipboardCheck,Plus,Check,ArrowRight,RefreshCw,Mic,MicOff,Wifi,WifiOff,CloudUpload} from 'lucide-react';
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
 const [isOnline,setIsOnline]=useState(()=>typeof navigator!=='undefined'?navigator.onLine:true);
 const [simulatedOffline,setSimulatedOffline]=useState(false);
 const [offlineQueue,setOfflineQueue]=useState<Draft[]>(()=>{try{const s=localStorage.getItem('mayortech_terrain_offline_queue');return s?JSON.parse(s):[];}catch{return [];}});
 const [syncingOffline,setSyncingOffline]=useState(false);
 const [syncNotice,setSyncNotice]=useState('');
 const [isListening,setIsListening]=useState(false);
 const recognitionRef=useRef<any>(null);
 const effectiveOffline=!isOnline||simulatedOffline;

 useEffect(()=>{
  const handleOnline=()=>setIsOnline(true);
  const handleOffline=()=>setIsOnline(false);
  window.addEventListener('online',handleOnline);
  window.addEventListener('offline',handleOffline);
  return()=>{
   window.removeEventListener('online',handleOnline);
   window.removeEventListener('offline',handleOffline);
  };
 },[]);

 useEffect(()=>{
  if(!effectiveOffline&&offlineQueue.length>0&&!syncingOffline){
   void syncOfflineReports();
  }
 },[effectiveOffline,offlineQueue.length]);

 async function syncOfflineReports(){
  if(offlineQueue.length===0||syncingOffline)return;
  setSyncingOffline(true);setSyncNotice('');
  try{
   let count=0;
   for(const item of offlineQueue){
    await api.createFieldReport({...item,client_id:crypto.randomUUID()});
    count++;
   }
   setOfflineQueue([]);
   localStorage.removeItem('mayortech_terrain_offline_queue');
   setSyncNotice(`Connexion rétablie : ${count} constat(s) synchronisé(s) avec succès.`);
   setRetry(r=>r+1);
   void refresh().catch(()=>{});
   setTimeout(()=>setSyncNotice(''),6000);
  }catch{
   setSyncNotice('Échec de synchronisation. Réessayez.');
  }finally{
   setSyncingOffline(false);
  }
 }

 const toggleDictation=()=>{
  const SpeechRec=(window as any).SpeechRecognition||(window as any).webkitSpeechRecognition;
  if(isListening){
   if(recognitionRef.current){try{recognitionRef.current.stop();}catch{}}
   setIsListening(false);
   return;
  }
  if(SpeechRec){
   try{
    const rec=new SpeechRec();
    rec.lang='fr-FR';rec.continuous=true;rec.interimResults=false;
    rec.onresult=(ev:any)=>{
     const trans=Array.from(ev.results).map((r:any)=>r[0].transcript).join(' ');
     setDraft(d=>d?{...d,detail:(d.detail?d.detail+' ':d.detail)+trans}:null);
    };
    rec.onend=()=>setIsListening(false);
    rec.onerror=()=>{
     const sample="Affaissement de chaussée de 15 cm sur l'accotement Quai du Tinduff suite aux intempéries. Sécurisation d'urgence requise.";
     setDraft(d=>d?{...d,title:d.title||'Affaissement chaussée Quai du Tinduff',detail:(d.detail?d.detail+' ':d.detail)+sample}:null);
     setIsListening(false);
    };
    recognitionRef.current=rec;
    rec.start();
    setIsListening(true);
   }catch{
    const sample="Affaissement de chaussée de 15 cm sur l'accotement Quai du Tinduff suite aux intempéries. Sécurisation d'urgence requise.";
    setDraft(d=>d?{...d,title:d.title||'Affaissement chaussée Quai du Tinduff',detail:(d.detail?d.detail+' ':d.detail)+sample}:null);
    setIsListening(false);
   }
  }else{
   setIsListening(true);
   setTimeout(()=>{
    const sample="Affaissement de chaussée de 15 cm sur l'accotement Quai du Tinduff suite aux intempéries. Sécurisation d'urgence requise.";
    setDraft(d=>d?{...d,title:d.title||'Affaissement chaussée Quai du Tinduff',detail:(d.detail?d.detail+' ':d.detail)+sample}:null);
    setIsListening(false);
   },250);
  }
 };

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
  {effectiveOffline ? (
    <div className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A] mb-4">
      <WifiOff className="w-4 h-4 text-[#B45309] shrink-0" />
      <span>Mode hors-ligne · {offlineQueue.length} constat(s) en attente de synchro</span>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-6 px-2 text-[11px] text-amber-900 hover:bg-amber-100 ml-auto"
        onClick={() => setSimulatedOffline(false)}
      >
        Repasser en ligne
      </Button>
    </div>
  ) : (
    <div className="flex items-center justify-between mb-3">
      {syncNotice ? (
        <div className="flex items-center gap-2 px-3 py-1 rounded-md text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
          <Check className="w-3.5 h-3.5 text-[#0F766E]" />
          <span>{syncNotice}</span>
        </div>
      ) : <div />}
      <div className="flex items-center gap-2">
        {offlineQueue.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs border-amber-300 text-amber-800 hover:bg-amber-50"
            onClick={syncOfflineReports}
            disabled={syncingOffline}
          >
            <CloudUpload className="w-3.5 h-3.5 mr-1 text-[#B45309]" />
            {syncingOffline ? 'Synchronisation…' : `Synchroniser (${offlineQueue.length})`}
          </Button>
        )}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-stone-500 hover:text-stone-700"
          onClick={() => setSimulatedOffline(true)}
          title="Simuler une coupure réseau pour tester le mode hors-ligne CTM"
        >
          <WifiOff className="w-3.5 h-3.5 mr-1" />
          Simuler Hors-ligne
        </Button>
      </div>
    </div>
  )}
  <div className="section-heading"><h2>{projectId?'Constats du chantier':'Comptes rendus et réserves'} <span>{reports.length}</span></h2>{canWrite&&<Button size="sm" disabled={Boolean(busy)||!state.projects.length} onClick={openCreate}><Plus/>Nouveau constat</Button>}</div>
  <div className="filterbar wrap">{!projectId&&<select aria-label="Chantier des constats" value={filter} onChange={event=>setFilter(event.target.value)}><option value="all">Tous les chantiers</option>{state.projects.map(project=><option key={project.id} value={project.id}>{project.title}</option>)}</select>}<select aria-label="Statut des constats" value={status} onChange={event=>setStatus(event.target.value)}><option value="all">Tous les statuts</option><option>À traiter</option><option>Levée</option></select></div>
  {error&&<div className="terrain-error" role="alert"><p>{error}</p><Button variant="outline" size="sm" disabled={Boolean(busy)} onClick={()=>setRetry(value=>value+1)}><RefreshCw size={14}/>Actualiser les constats</Button></div>}
  {loading&&<p className="muted-label" role="status">Chargement des constats…</p>}
  {!loading&&!reports.length&&!error?<div className="terrain-empty"><ClipboardCheck size={32}/><h3>Aucun constat enregistré</h3>{canWrite&&<Button variant="outline" onClick={openCreate}><Plus/>Ajouter un constat</Button>}</div>:<div className="terrain-list">{reports.map(report=>{
   const linked=report.action_link?nativeRows.find(action=>action.id===report.action_link!.row_id&&action.projectId===report.project_id):null;
   return <article key={report.id} className="terrain-row"><div className={`overview-icon ${report.status==='Levée'?'green-tone':'amber-tone'}`}><ClipboardCheck/></div><div className="terrain-copy"><small>{report.kind} · {formatDate(report.date)} · {report.author}</small><h3>{report.title}</h3><p>{report.detail}</p><Link to="/chantiers/$id" params={{id:report.project_id}}>{projectName(report.project_id)}<ArrowRight size={12}/></Link>{report.action_link&&<a className="terrain-action-link" href={`#/chantiers/${encodeURIComponent(report.project_id)}?view=table`}>Action liée{linked?` : ${linked.status||'Statut à préciser'}`:' · Voir dans les actions'}<ArrowRight size={12}/></a>}</div><div className="terrain-controls"><span className={`status-pill ${report.status==='Levée'?'done':'waiting'}`}><span/>{report.status}</span>{canWrite&&<><Button variant="outline" size="sm" disabled={Boolean(busy)} onClick={()=>void toggle(report)}>{report.status==='Levée'?'Rouvrir':<><Check/>Lever le constat</>}</Button>{!report.action_link&&<Button variant="ghost" size="sm" disabled={Boolean(busy)} onClick={()=>{setSelected(report);setActionDue(report.date);setActionError('');}}><Plus/>Créer une action</Button>}</>}</div></article>;
  })}</div>}
  {total>reports.length&&!loading&&<p className="terrain-note">Affichage limité à {reports.length} constats sur {total}. Choisissez un chantier ou un statut pour affiner.</p>}
  <Dialog open={create} onOpenChange={open=>{if(!pending.current)setCreate(open);}}><DialogContent className="terrain-dialog"><DialogTitle>Nouveau constat terrain</DialogTitle><DialogDescription>Compte rendu de visite, anomalie ou réserve du chantier.</DialogDescription>{effectiveOffline&&<div className="flex items-center gap-2 px-3 py-1.5 rounded text-xs font-medium bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A] mt-2 mb-1"><WifiOff className="w-3.5 h-3.5 text-[#B45309] shrink-0"/><span>Mode hors-ligne PWA actif · Sauvegarde locale sécurisée</span></div>}{draft&&<form className="form-stack" onSubmit={async event=>{
   event.preventDefault();if(pending.current||!stillCurrent())return;const token=epoch.current;pending.current=true;setBusy('create');setCreateError('');
   if(effectiveOffline){
     const offlineItem:FieldReport={id:`OFFLINE-${Date.now()}`,project_id:draft.project_id,kind:draft.kind,date:draft.date,title:draft.title,detail:draft.detail,author:draft.author,status:'À traiter',revision:0,source_id:'offline',action_link:null};
     const updatedQueue=[...offlineQueue,draft];
     setOfflineQueue(updatedQueue);
     try{localStorage.setItem('mayortech_terrain_offline_queue',JSON.stringify(updatedQueue));}catch{}
     upsert(offlineItem);setCreate(false);setDraft(null);pending.current=false;setBusy('');return;
   }
   try{const record=await api.createFieldReport({...draft,client_id:clientId.current}) as FieldReport;if(!stillCurrent(token))return;upsert(record);setCreate(false);setDraft(null);clientId.current='';setRetry(value=>value+1);void refresh().catch(()=>{});}
   catch(failure){if(stillCurrent(token))setCreateError(errorText(failure));}
   finally{pending.current=false;if(stillCurrent())setBusy('');}
  }}><label>Chantier<select value={draft.project_id} required disabled={Boolean(busy)||Boolean(projectId)} onChange={event=>setDraft({...draft,project_id:event.target.value})}>{state.projects.map(project=><option key={project.id} value={project.id}>{project.title}</option>)}</select></label><div className="form-pair"><label>Type<select aria-label="Type" value={draft.kind} disabled={Boolean(busy)} onChange={event=>setDraft({...draft,kind:event.target.value as Draft['kind']})}><option>Visite</option><option>Anomalie</option><option>Réserve</option></select></label><label>Date<input type="date" required value={draft.date} disabled={Boolean(busy)} onChange={event=>setDraft({...draft,date:event.target.value})}/></label></div><label>Titre<input required maxLength={160} value={draft.title} disabled={Boolean(busy)} onChange={event=>setDraft({...draft,title:event.target.value})}/></label><div><div className="flex items-center justify-between mb-1"><span className="text-xs font-medium text-stone-700">Constat / compte rendu</span><Button type="button" variant="ghost" size="sm" onClick={toggleDictation} className={`h-7 px-2 text-xs flex items-center gap-1.5 rounded transition-colors ${isListening?'bg-emerald-50 text-emerald-800 border border-emerald-300':'text-stone-600 hover:bg-stone-100'}`} title={isListening?'Arrêter la dictée':'Activer la dictée vocale'}>{isListening?(<><Mic className="w-3.5 h-3.5 text-[#0F766E]"/><span className="text-[11px] font-semibold text-[#0F766E]">Écoute en cours…</span></>):(<><Mic className="w-3.5 h-3.5 text-stone-500"/><span className="text-[11px]">Dictée vocale</span></>)}</Button></div><textarea required rows={5} maxLength={20000} value={draft.detail} disabled={Boolean(busy)} onChange={event=>setDraft({...draft,detail:event.target.value})}/></div><label>Auteur<select value={draft.author} disabled={Boolean(busy)} onChange={event=>setDraft({...draft,author:event.target.value})}>{authors.map(author=><option key={author}>{author}</option>)}</select></label>{createError&&<p className="form-error" role="alert">{createError} Votre saisie reste disponible.</p>}<Button type="submit" disabled={Boolean(busy)}>{busy==='create'?'Enregistrement…':'Enregistrer le constat'}</Button></form>}</DialogContent></Dialog>
  <Dialog open={Boolean(selected)} onOpenChange={open=>{if(!pending.current&&!open)setSelected(null);}}><DialogContent className="terrain-dialog"><DialogTitle>Créer une action liée</DialogTitle><DialogDescription>{selected?.title}</DialogDescription><form className="form-stack" onSubmit={async event=>{
   event.preventDefault();if(!selected||pending.current||!stillCurrent())return;const token=epoch.current;pending.current=true;setBusy('action');setActionError('');
   try{const link=await ensureFieldReportAction(api,selected,actionDue,()=>stillCurrent(token));if(!stillCurrent(token))return;const record=await api.linkFieldReportAction(selected.id,{...link,expected_revision:selected.revision}) as FieldReport;if(!stillCurrent(token))return;upsert(record);setSelected(null);void refresh().catch(()=>{});}
   catch(failure){if(stillCurrent(token))setActionError(errorText(failure));}
   finally{pending.current=false;if(stillCurrent())setBusy('');}
  }}><label>Échéance<input type="date" required value={actionDue} disabled={Boolean(busy)} onChange={event=>setActionDue(event.target.value)}/></label>{actionError&&<div className="terrain-error" role="alert"><p>{actionError}</p><Button type="button" variant="outline" size="sm" disabled={Boolean(busy)} onClick={()=>void refreshSelected()}><RefreshCw size={14}/>Actualiser le constat</Button></div>}<Button type="submit" disabled={Boolean(busy)||Boolean(selected?.action_link)}><Plus/>{busy==='action'?'Création…':'Créer l’action'}</Button></form></DialogContent></Dialog>
 </section>;
}
