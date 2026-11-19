import {useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {CalendarDays,CalendarCheck2,ChartGantt,ExternalLink,List,MoveHorizontal,RefreshCw} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useWorkspace} from './context';
import {formatDate} from './model';
import {cachedNativeActions,changeNativeAction,flushNativeActions,loadNativeActions,type NativeAction} from './native-actions';
import {registerPreserver} from './panel-lifecycle';
import {calendarEventsOf,dayFromGanttDate,ganttTasks,planningMilestones,safeCalendarUrl,scheduleOf,scheduleFormPatch,timelineAction,validDay,type CalendarEvent,type GanttTask} from './planning-model.mjs';
import type {ProjectRecord} from './ProjectPanels.types';
import {PlanningTimeline} from './PlanningTimeline';
import {PlanningActionDialog} from './PlanningActionDialog';
import './planning.css';

type Patch=Record<string,string|number>;
type GanttInstance={destroy():void;config:{column_width:number}};
type CalendarApi={calendarEvents?:(query:Record<string,string>)=>Promise<unknown>};
interface QueuedEdit {action:NativeAction;patch:Patch}

function eventDate(event:CalendarEvent){
 if(event.all_day)return `${formatDate(event.start.slice(0,10))} · Toute la journée`;
 const formatter=new Intl.DateTimeFormat('fr-FR',{timeZone:'Europe/Paris',day:'numeric',month:'long',hour:'2-digit',minute:'2-digit'});
 return formatter.format(new Date(event.start));
}

/** Dates, progress and provenance remain fields of the existing native action. */
export function Planning({project,onSource,onChanged}:{project:ProjectRecord;onSource?:(sourceId:string)=>void;onChanged?:()=>Promise<void>|void}){
 const {api,bootstrap,state}=useWorkspace();const canWrite=bootstrap?.permissions?.workspace?.write===true;
 const hasConfirmedActions=project.actions.length>0;
 const [items,setItems]=useState<NativeAction[]>(()=>cachedNativeActions([project.id]));
 const [loading,setLoading]=useState(true),[error,setError]=useState(''),[calendarError,setCalendarError]=useState(''),[events,setEvents]=useState<CalendarEvent[]>([]);
 const [view,setView]=useState<'timeline'|'gantt'|'list'>(()=>typeof matchMedia!=='undefined'&&matchMedia('(max-width:640px)').matches?'list':'timeline');
 const [month,setMonth]=useState(()=>dayFromGanttDate(new Date()).slice(0,7));
 const [scale,setScale]=useState('Day'),[busy,setBusy]=useState(false),[saveState,setSaveState]=useState(''),[chartEpoch,setChartEpoch]=useState(0),[chartError,setChartError]=useState('');
 const [selected,setSelected]=useState<NativeAction|null>(null),[start,setStart]=useState(''),[end,setEnd]=useState(''),[progress,setProgress]=useState(''),[owner,setOwner]=useState(''),[status,setStatus]=useState(''),[formError,setFormError]=useState('');
 const [dialogOpen,setDialogOpen]=useState(false);
 const alive=useRef(true),busyRef=useRef(false),itemsRef=useRef(items),host=useRef<HTMLDivElement>(null),queued=useRef(new Map<string,QueuedEdit>()),saving=useRef<Promise<void>|null>(null),flushRef=useRef<()=>Promise<void>>(async()=>{}),contextChanged=useRef(onChanged);
 contextChanged.current=onChanged;
 itemsRef.current=items;
 const commitRows=useCallback((rows:NativeAction[])=>setItems(previous=>previous.length===rows.length&&previous.every((item,index)=>item.id===rows[index].id&&item.fingerprint===rows[index].fingerprint&&item.source===rows[index].source)?previous:rows),[]);
 const notifyContext=useCallback(()=>{void Promise.resolve().then(()=>contextChanged.current?.()).catch(()=>{if(alive.current)setError('Les dates sont enregistrées, mais le contexte du dossier n’a pas pu être actualisé. Rechargez le dossier.');});},[]);
 const loadCalendar=useCallback(async()=>{
  try{const calendar=api as unknown as CalendarApi;if(!calendar.calendarEvents)throw Error('Les agendas ne sont pas disponibles dans cette version.');const value=await calendar.calendarEvents({project_id:project.id});if(alive.current){setEvents(calendarEventsOf(value,project.id));setCalendarError('');}}
  catch(failure){if(alive.current)setCalendarError(failure instanceof Error?failure.message:'Les rendez-vous ne peuvent pas être chargés.');}
 },[api,project.id]);
 const load=useCallback(async()=>{
  setLoading(true);setError('');
  try{await loadNativeActions(api,[project.id],canWrite,hasConfirmedActions?[project.id]:[]);if(alive.current)commitRows(cachedNativeActions([project.id]));}
  catch(failure){if(alive.current)setError(failure instanceof Error?failure.message:'Le planning ne peut pas être chargé. Réessayez.');}
  finally{if(alive.current)setLoading(false);}
 },[api,project.id,canWrite,commitRows,hasConfirmedActions]);

 const flushQueued=useCallback(()=>{
  if(saving.current)return saving.current;
  if(!queued.current.size)return Promise.resolve();
  busyRef.current=true;if(alive.current){setBusy(true);setError('');setSaveState('Enregistrement du planning…');}
  const task=(async()=>{
   while(queued.current.size){
    const edit=queued.current.values().next().value as QueuedEdit;queued.current.delete(edit.action.id);
    await changeNativeAction(api,edit.action,edit.patch);
   }
   if(alive.current){commitRows(cachedNativeActions([project.id]));setSaveState('');notifyContext();}
  })().catch(failure=>{
   queued.current.clear();
   if(alive.current){setError((failure instanceof Error?failure.message:'Le planning n’a pas été enregistré.')+' Les dates affichées ont été rétablies ; actualisez avant de réessayer.');setSaveState('Modification non enregistrée.');setChartEpoch(value=>value+1);}
   throw failure;
  }).finally(()=>{saving.current=null;busyRef.current=false;if(alive.current)setBusy(false);});
  saving.current=task;return task;
 },[api,project.id,commitRows,notifyContext]);
 flushRef.current=flushQueued;

 useEffect(()=>{
  alive.current=true;commitRows(cachedNativeActions([project.id]));void load();void loadCalendar();
  const changed=()=>{if(alive.current)commitRows(cachedNativeActions([project.id]));};window.addEventListener('travaux:native-actions',changed);
  const unregister=registerPreserver(async()=>{await flushRef.current();await flushNativeActions();},()=>Boolean(queued.current.size||busyRef.current));
  return()=>{alive.current=false;window.removeEventListener('travaux:native-actions',changed);unregister();};
 },[project.id,load,loadCalendar,commitRows]);

 const planned=useMemo(()=>items.filter(action=>scheduleOf(action)),[items]);
 const unplanned=useMemo(()=>items.filter(action=>!scheduleOf(action)),[items]);
 const deadline=state.projects.find(item=>item.id===project.id)?.deadline;
 const milestones=useMemo(()=>[...planningMilestones(project,deadline).map(item=>({...item,pending:false})),...project.pending.filter(item=>item.kind==='date'&&validDay(item.value)&&['delivery_date','deadline','acceptance_date'].includes(item.field)).map(item=>({id:item.id,label:item.label,date:String(item.value),sourceId:item.source_id,confirmed:false,pending:true}))].sort((a,b)=>a.date.localeCompare(b.date)),[project.facts,project.pending,deadline]);
 const timelineHasDates=milestones.some(item=>!item.pending)||items.some(action=>timelineAction(action));
 const open=useCallback((action:NativeAction)=>{
  if(busyRef.current||queued.current.size)return;
  setDialogOpen(true);setSelected(action);setStart(action.start||'');setEnd(action.due||'');setProgress(typeof action.progress==='number'?String(action.progress):'');setOwner(action.owner);setStatus(action.status);setFormError('');
 },[]);
 const openRef=useRef(open);openRef.current=open;

 useEffect(()=>{
  if(view!=='gantt'||!planned.length||!host.current)return;
  let disposed=false,chart:GanttInstance|undefined;
  const element=host.current;setChartError('');
  const mapped=ganttTasks(planned);
  const span=Math.ceil((Math.max(...mapped.tasks.map(task=>Date.parse(task.end)))-Math.min(...mapped.tasks.map(task=>Date.parse(task.start))))/86400000);
  const dayColumnWidth=Math.max(36,Math.floor(element.clientWidth/(span+16)));
  const collect=(task:GanttTask,patch:Patch)=>{
   const action=mapped.actions.get(task.id);if(!canWrite||!action||busyRef.current)return;
   const previous=queued.current.get(action.id);queued.current.set(action.id,{action:previous?.action||action,patch:{...previous?.patch,...patch}});
   setSaveState('Dates modifiées…');
  };
  const release=()=>{if(!disposed&&queued.current.size)void flushRef.current().catch(()=>{});};
  const keys=(event:KeyboardEvent)=>{
   if(event.key!=='Enter'&&event.key!==' ')return;const wrapper=(event.target as Element).closest('[data-planning-action]');if(!wrapper)return;
   const action=itemsRef.current.find(item=>item.id===wrapper.getAttribute('data-planning-action'));if(action){event.preventDefault();openRef.current(action);}
  };
  document.addEventListener('mouseup',release);element.addEventListener('keydown',keys);
  void import('../../vendor/frappe-gantt/index.js').then(({default:Gantt})=>{
   if(disposed)return;
   chart=new Gantt(element,mapped.tasks,{
    language:'fr',view_mode:scale,column_width:scale==='Day'?dayColumnWidth:null,infinite_padding:false,scroll_to:'start',today_button:false,view_mode_select:false,
    upper_header_height:32,lower_header_height:28,bar_height:28,padding:20,container_height:Math.min(420,Math.max(180,planned.length*48+80)),
    readonly:!canWrite,readonly_dates:!canWrite,readonly_progress:!canWrite,move_dependencies:false,show_expected_progress:false,popup:false,
    on_click:(task:GanttTask)=>{const action=mapped.actions.get(task.id);if(action)openRef.current(action);},
    on_date_change:(task:GanttTask,begin:Date,finish:Date)=>{const first=dayFromGanttDate(begin),last=dayFromGanttDate(finish);if(validDay(first)&&validDay(last)&&first<=last)collect(task,{startDate:first,dueDate:last});},
    on_progress_change:(task:GanttTask,value:number)=>{const action=mapped.actions.get(task.id);if(typeof action?.progress==='number'&&Number.isFinite(value))collect(task,{progress:Math.max(0,Math.min(100,Math.round(value)))});},
   }) as GanttInstance;
   element.dataset.columnWidth=String(chart.config.column_width);
   for(const wrapper of element.querySelectorAll<SVGElement>('.bar-wrapper')){
    const action=mapped.actions.get(wrapper.getAttribute('data-id')||'');if(!action)continue;
    wrapper.dataset.planningAction=action.id;wrapper.setAttribute('tabindex','0');wrapper.setAttribute('role','button');wrapper.setAttribute('aria-label',`${canWrite?'Modifier':'Consulter'} ${action.title}, du ${formatDate(action.start||'')} au ${formatDate(action.due)}`);
   }
  }).catch(()=>{if(!disposed)setChartError('La frise ne peut pas être affichée. La liste et les formulaires restent disponibles.');});
  return()=>{disposed=true;document.removeEventListener('mouseup',release);element.removeEventListener('keydown',keys);chart?.destroy();element.replaceChildren();};
 },[planned,scale,view,canWrite,chartEpoch]);

 async function saveForm(){
  if(!selected||busyRef.current||!canWrite)return;
  setFormError('');let patch:Patch;
  try{patch=scheduleFormPatch(selected,start,end,progress,owner,status);}catch(failure){setFormError(failure instanceof Error?failure.message:'Vérifiez les dates.');return;}
  busyRef.current=true;setBusy(true);
  try{await changeNativeAction(api,selected,patch);commitRows(cachedNativeActions([project.id]));setSelected(null);setDialogOpen(false);setSaveState('');notifyContext();}
  catch(failure){setFormError(failure instanceof Error?failure.message:'La modification n’a pas été enregistrée. Votre saisie est conservée.');}
  finally{busyRef.current=false;if(alive.current)setBusy(false);}
 }

 return <section className="planning-section" aria-label="Planning du chantier">
  <h2 className="sr-only">Planning du chantier</h2>
  {milestones.some(item=>view!=='timeline'||item.pending)&&<ul className="planning-milestones" aria-label="Dates clés du dossier">{milestones.filter(item=>view!=='timeline'||item.pending).map(item=><li key={item.id} className={item.pending?'proposed':'confirmed'}><CalendarCheck2 size={17}/><div><strong>{item.pending?'À confirmer':item.label}</strong><span>{formatDate(item.date)}{item.pending?` · ${item.label.toLocaleLowerCase('fr')}`:item.confirmed?' · Date confirmée':' · Date du dossier'}</span></div>{onSource&&item.sourceId&&<Button variant="ghost" size="sm" onClick={()=>onSource(item.sourceId!)}>Source<ExternalLink size={12}/></Button>}</li>)}</ul>}
  <div className="planning-toolbar"><div className="planning-view-switch" aria-label="Présentation du planning"><Button variant={view==='timeline'?'secondary':'ghost'} size="sm" aria-pressed={view==='timeline'} onClick={()=>setView('timeline')}><ChartGantt size={15}/>Frise</Button><Button variant={view==='gantt'?'secondary':'ghost'} size="sm" aria-pressed={view==='gantt'} onClick={()=>setView('gantt')}><MoveHorizontal size={15}/>Déplacer</Button><Button variant={view==='list'?'secondary':'ghost'} size="sm" aria-pressed={view==='list'} onClick={()=>setView('list')}><List size={15}/>Liste</Button></div>{view==='gantt'&&planned.length>0&&<label className="planning-scale">Échelle<select value={scale} onChange={event=>setScale(event.target.value)}><option value="Day">Jours</option><option value="Week">Semaines</option><option value="Month">Mois</option></select></label>}{(busy||saveState)&&<span className="planning-save" role="status">{busy?'Enregistrement…':saveState}</span>}<div className="planning-heading-actions"><Button variant="ghost" size="icon" aria-label="Actualiser le planning" disabled={loading||busy} onClick={()=>{void load();void loadCalendar();}}><RefreshCw size={15}/></Button>{canWrite&&items.length>0&&<Button size="sm" disabled={busy} aria-label="Planifier une action" onClick={()=>{setSelected(null);setFormError('');setDialogOpen(true);}}><CalendarDays size={15}/><span className="planning-action-label-desktop">Planifier une action</span><span className="planning-action-label-mobile">Planifier</span></Button>}</div></div>
  {loading&&<p className="planning-status" role="status">Chargement du suivi enregistré…</p>}
  {error&&<div className="form-error" role="alert">{error}<Button variant="link" onClick={()=>void load()}>Actualiser les actions</Button></div>}
  {view==='timeline'&&(timelineHasDates||loading||Boolean(error))&&<><PlanningTimeline groups={[{project,actions:items,deadline}]} month={month} onMonth={setMonth} onAction={open} onSource={onSource} canWrite={canWrite} loading={loading} unavailable={Boolean(error)}/><p className="planning-caption">Cliquez sur une action pour consulter ou modifier ses dates. Le mode Déplacer permet de glisser les barres.</p></>}
  {view==='gantt'&&!loading&&!planned.length&&timelineHasDates&&<div className="planning-empty"><div><h3>Des échéances sont disponibles</h3><p>Déplacer une barre nécessite un début et une fin. Les échéances seules restent visibles dans la frise.</p><Button variant="outline" onClick={()=>setView('timeline')}>Voir les échéances</Button></div></div>}
  {view==='gantt'&&planned.length>0&&<><div className="planning-gantt" data-saving={busy} ref={host} aria-label="Frise éditable des actions"/>{chartError&&<p className="form-error" role="alert">{chartError}</p>}<p className="planning-caption">Glissez une barre pour déplacer ses dates, ou cliquez dessus pour ouvrir le formulaire. L’avancement vide reste non renseigné.</p></>}
  {view==='list'&&planned.length>0&&<div className="planning-action-list" aria-label="Actions planifiées">{planned.map(action=><article key={action.id} data-planning-row={action.id}><div><Button variant="link" onClick={()=>open(action)}>{action.title}</Button><p>{action.owner||'À attribuer'} · {action.status||'Statut non renseigné'}</p></div><span>{formatDate(action.start||'')} → {formatDate(action.due)}</span><span>{typeof action.progress==='number'?`${action.progress} %`:'Avancement non renseigné'}</span><Button variant="outline" size="sm" onClick={()=>open(action)}>{canWrite?'Modifier':'Consulter'}</Button></article>)}</div>}
  {!loading&&!error&&!timelineHasDates&&<div className="planning-empty"><CalendarDays size={24}/><div><h3>Aucune période ou échéance à afficher</h3><p>Les actions restent disponibles dans le suivi. Une échéance seule sera affichée comme un jalon, sans inventer de début.</p>{canWrite&&<a href={`#/chantiers/${encodeURIComponent(project.id)}?view=table`}>Créer une action</a>}</div></div>}
  {unplanned.length>0&&<section className="planning-unplanned"><div className="section-heading"><h3>Dates à compléter <span>{unplanned.length}</span></h3></div><div className="planning-action-list">{unplanned.map(action=><article key={action.id} data-planning-row={action.id}><div><strong>{action.title}</strong><p>{action.owner||'À attribuer'} · {action.status||'Statut non renseigné'}</p></div><span>{validDay(action.due)?`Échéance : ${formatDate(action.due)}`:'Échéance non renseignée'}</span><Button variant="outline" size="sm" disabled={busy} onClick={()=>open(action)}>{canWrite?'Planifier':'Consulter'}</Button></article>)}</div></section>}
  <section className="planning-calendar"><div className="section-heading"><h3>Rendez-vous des agendas <span>{events.length}</span></h3><a href="#/parametres?section=connections">Gérer les connexions<ExternalLink size={12}/></a></div>{calendarError?<p className="form-error" role="alert">{calendarError} <Button variant="link" onClick={()=>void loadCalendar()}>Réessayer</Button></p>:events.length?<ul>{events.map(event=>{const url=safeCalendarUrl(event.source_url);return <li key={event.id}><CalendarDays size={18}/><div><strong>{event.title}</strong><p>{eventDate(event)} · {event.calendar_name}{event.status==='tentative'?' · À confirmer':event.status==='cancelled'?' · Annulé':''}</p></div>{url&&<a href={url} target="_blank" rel="noreferrer noopener" aria-label={`Ouvrir ${event.title} dans l’agenda`}><ExternalLink size={15}/></a>}</li>;})}</ul>:<p className="planning-status">Aucun rendez-vous d’agenda n’est rattaché à ce chantier.</p>}</section>
  <PlanningActionDialog open={dialogOpen} projectId={project.id} items={items} projects={state.projects} selected={selected} canWrite={canWrite} busy={busy} start={start} end={end} progress={progress} owner={owner} status={status} owners={state.members.map(member=>member.name)} error={formError} onSelect={open} onClearSelection={()=>{setSelected(null);setFormError('');}} onStart={setStart} onEnd={setEnd} onProgress={setProgress} onOwner={setOwner} onStatus={setStatus} onSave={saveForm} onClose={()=>{setSelected(null);setDialogOpen(false);}} onSource={onSource}/>
 </section>;
}
