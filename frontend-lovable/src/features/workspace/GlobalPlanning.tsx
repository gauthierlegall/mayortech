import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {CalendarDays,ChartGantt,List,RefreshCw} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {formatDate} from './model';
import {cachedNativeActions,changeNativeAction,flushNativeActions,loadNativeActions,type NativeAction} from './native-actions';
import {registerPreserver} from './panel-lifecycle';
import {dayFromGanttDate,loadPlanningProjects,planningMilestones,scheduleOf,scheduleFormPatch,validDay} from './planning-model.mjs';
import {projectOf,type ProjectRecord} from './ProjectPanels.types';
import {PlanningTimeline} from './PlanningTimeline';
import {PlanningActionDialog} from './PlanningActionDialog';
import {RoadTrafficConflictBanner} from './RoadTrafficConflictBanner';
import {SourcePreview} from './SourcePreview';
import './planning.css';

export function GlobalPlanning(){
 const {state,api,bootstrap,refresh}=useWorkspace(),canWrite=bootstrap?.permissions?.workspace?.write===true;
 const ids=useMemo(()=>state.projects.map(project=>project.id),[state.projects.map(project=>project.id).join('|')]);
 const [projects,setProjects]=useState<ProjectRecord[]>([]),[items,setItems]=useState<NativeAction[]>(()=>cachedNativeActions(ids)),[loading,setLoading]=useState(true),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [month,setMonth]=useState(()=>dayFromGanttDate(new Date()).slice(0,7)),[filter,setFilter]=useState(''),[view,setView]=useState<'timeline'|'list'>(()=>typeof matchMedia!=='undefined'&&matchMedia('(max-width:640px)').matches?'list':'timeline');
 const [selected,setSelected]=useState<NativeAction|null>(null),[start,setStart]=useState(''),[end,setEnd]=useState(''),[progress,setProgress]=useState(''),[owner,setOwner]=useState(''),[status,setStatus]=useState(''),[formError,setFormError]=useState(''),[source,setSource]=useState<{id:string;focus:HTMLElement|null}|null>(null);
 const [dialogOpen,setDialogOpen]=useState(false);
 const alive=useRef(true),pending=useRef(false),loadEpoch=useRef(0);
 const load=useCallback(async()=>{
  const token=++loadEpoch.current;setLoading(true);setError('');
  const details=await loadPlanningProjects(ids,async id=>projectOf(await api.project(id)));
  if(!alive.current||token!==loadEpoch.current)return;
  setProjects(details.projects);
  const failures:string[]=details.failed?['Certains dossiers n’ont pas pu être chargés. Les dates disponibles restent affichées.']:[];
  try{await loadNativeActions(api,ids,canWrite,details.projects.filter(project=>project.actions.length>0).map(project=>project.id));}
  catch(failure){failures.push(failure instanceof Error?failure.message:'Certaines actions n’ont pas pu être chargées. Réessayez.');}
  if(!alive.current||token!==loadEpoch.current)return;
  setItems(cachedNativeActions(ids));
  setError(failures.join(' '));
  setLoading(false);
 },[api,ids,canWrite]);
 useEffect(()=>{
  alive.current=true;void load();
  const changed=()=>{if(alive.current)setItems(cachedNativeActions(ids));};
  window.addEventListener('travaux:native-actions',changed);
  const unregister=registerPreserver(async()=>{if(pending.current)throw Error('Attendez l’enregistrement des dates avant de quitter le planning.');await flushNativeActions();},()=>pending.current);
  return()=>{alive.current=false;loadEpoch.current++;window.removeEventListener('travaux:native-actions',changed);unregister();};
 },[ids,load]);
 const actions=items.filter(action=>!filter||action.projectId===filter),planned=actions.filter(action=>scheduleOf(action)),unplanned=actions.filter(action=>!scheduleOf(action));
 const groups=state.projects.filter(project=>!filter||project.id===filter).map(base=>({project:projects.find(project=>project.id===base.id)||{id:base.id,name:base.title,reference:base.ref,facts:[],pending:[]},actions:actions.filter(action=>action.projectId===base.id),deadline:base.deadline}));
 const dossierMilestones=groups.flatMap(group=>planningMilestones(group.project,group.deadline).map(item=>({project:group.project,item})));
 const proposals=groups.flatMap(({project})=>project.pending.filter(item=>item.kind==='date'&&validDay(item.value)&&['delivery_date','deadline','acceptance_date'].includes(item.field)).map(item=>({project,item})));
 const projectFilter=<label className="planning-project-filter"><span className="sr-only">Chantier</span><select aria-label="Chantier du planning" value={filter} onChange={event=>setFilter(event.target.value)}><option value="">Tous les chantiers</option>{state.projects.map(project=><option key={project.id} value={project.id}>{project.title}</option>)}</select></label>;
 const open=(action:NativeAction)=>{if(pending.current)return;setDialogOpen(true);setSelected(action);setStart(action.start||'');setEnd(action.due||'');setProgress(typeof action.progress==='number'?String(action.progress):'');setOwner(action.owner);setStatus(action.status);setFormError('');};
 const openSource=(id:string)=>setSource({id,focus:document.activeElement instanceof HTMLElement?document.activeElement:null});
 async function save(){
  if(!selected||!canWrite||pending.current)return;
  let patch:Record<string,string|number>;
  try{patch=scheduleFormPatch(selected,start,end,progress,owner,status);}catch(failure){setFormError(failure instanceof Error?failure.message:'Vérifiez les dates.');return;}
  pending.current=true;setBusy(true);setFormError('');
  try{await changeNativeAction(api,selected,patch);setItems(cachedNativeActions(ids));setSelected(null);setDialogOpen(false);void refresh().catch(()=>{});}
  catch(failure){setFormError(failure instanceof Error?failure.message:'Les dates n’ont pas été enregistrées. Votre saisie est conservée.');}
  finally{pending.current=false;if(alive.current)setBusy(false);}
 }
 return <main className="content planning-section global-planning"><div className="page-heading"><div><h1>Planning</h1></div><div className="planning-heading-actions"><div className="planning-view-switch" aria-label="Présentation du planning"><Button size="icon" variant={view==='timeline'?'secondary':'ghost'} aria-label="Frise" aria-pressed={view==='timeline'} onClick={()=>setView('timeline')}><ChartGantt size={15}/></Button><Button size="icon" variant={view==='list'?'secondary':'ghost'} aria-label="Liste" aria-pressed={view==='list'} onClick={()=>setView('list')}><List size={15}/></Button></div><Button variant="ghost" size="icon" aria-label="Actualiser le planning" disabled={loading||busy} onClick={()=>void load()}><RefreshCw size={16}/></Button>{canWrite&&actions.length>0&&<Button size="sm" disabled={busy} onClick={()=>{setSelected(null);setFormError('');setDialogOpen(true);}}><CalendarDays size={15}/>Planifier une action</Button>}</div></div>
  <RoadTrafficConflictBanner/>
  {view==='list'&&<div className="planning-toolbar">{projectFilter}</div>}
  {loading&&<p className="planning-status" role="status">Chargement des plannings enregistrés…</p>}{error&&<div className="form-error" role="alert">{error} <Button variant="link" onClick={()=>void load()}>Réessayer</Button></div>}
  {view==='timeline'&&<PlanningTimeline groups={groups} month={month} onMonth={setMonth} onAction={open} onSource={openSource} canWrite={canWrite} controls={projectFilter} loading={loading} unavailable={Boolean(error)}/>}
  {view==='list'&&<div className="planning-action-list" aria-label="Actions planifiées">{planned.map(action=><article key={action.id} data-planning-row={action.id}><div><Button variant="link" onClick={()=>open(action)}>{action.title}</Button><p><a href={`#/chantiers/${encodeURIComponent(action.projectId)}?view=planning`}>{state.projects.find(project=>project.id===action.projectId)?.title}</a></p><p>{action.owner||'À attribuer'} · {action.status||'Statut non renseigné'}</p></div><span>{formatDate(action.start||'')} → {formatDate(action.due)}</span><span>{typeof action.progress==='number'?`${action.progress} %`:'Avancement non renseigné'}</span><Button variant="outline" size="sm" onClick={()=>open(action)}>{canWrite?'Modifier':'Consulter'}</Button></article>)}{!loading&&!error&&!planned.length&&<p className="planning-status">Aucune action avec début et fin pour cette sélection.</p>}</div>}
  {view==='list'&&dossierMilestones.length>0&&<section className="planning-dossier-dates"><h2>Dates des dossiers</h2><div className="planning-action-list">{dossierMilestones.map(({project,item})=><article key={`${project.id}:${item.id}`}><div><a href={`#/chantiers/${encodeURIComponent(project.id)}?view=planning`}>{project.name}</a><p>{item.label}</p></div><span>{formatDate(item.date)}</span>{item.sourceId&&<Button variant="link" onClick={()=>openSource(item.sourceId!)}>Source</Button>}</article>)}</div></section>}
  {proposals.length>0&&<details className="planning-pending"><summary>{proposals.length} date{proposals.length>1?'s':''} à confirmer</summary><ul>{proposals.map(({project,item})=><li key={item.id}><span>{project.name} · {item.label} proposée : {formatDate(String(item.value))}</span><Button variant="link" size="sm" onClick={()=>openSource(item.source_id)}>Examiner l’annonce</Button></li>)}</ul></details>}
  {unplanned.length>0&&<section className="planning-unplanned"><div className="section-heading"><h2>Dates à compléter <span>{unplanned.length}</span></h2></div><div className="planning-action-list">{unplanned.map(action=><article key={action.id} data-unplanned-row={action.id}><div><strong>{action.title}</strong><p>{state.projects.find(project=>project.id===action.projectId)?.title} · {action.owner||'À attribuer'}</p></div><span>{validDay(action.due)?`Échéance : ${formatDate(action.due)}`:'Échéance non renseignée'}</span><Button variant="outline" size="sm" disabled={busy} onClick={()=>open(action)}>{canWrite?'Planifier':'Consulter'}</Button></article>)}</div></section>}
  <PlanningActionDialog open={dialogOpen} items={items} projects={state.projects} selected={selected} canWrite={canWrite} busy={busy} start={start} end={end} progress={progress} owner={owner} status={status} owners={state.members.map(member=>member.name)} error={formError} onSelect={open} onClearSelection={()=>{setSelected(null);setFormError('');}} onStart={setStart} onEnd={setEnd} onProgress={setProgress} onOwner={setOwner} onStatus={setStatus} onSave={save} onClose={()=>{setSelected(null);setDialogOpen(false);}} onSource={openSource}/>
  <SourcePreview api={api} sourceId={source?.id||null} returnFocus={source?.focus||null} onClose={()=>setSource(null)}/>
 </main>;
}
