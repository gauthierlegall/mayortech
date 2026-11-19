import {ChevronLeft,ChevronRight,Diamond} from 'lucide-react';
import type {ReactNode} from 'react';
import {Button} from '@/components/ui/button';
import {formatDate} from './model';
import {dayFromGanttDate,monthWindow,planningMilestones,shiftMonth,timelineAction,timelineOverview,timelinePlacement} from './planning-model.mjs';
import type {NativeAction} from './native-actions';
import type {ProjectRecord} from './ProjectPanels.types';

export interface TimelineGroup {project:Pick<ProjectRecord,'id'|'name'|'reference'|'facts'|'properties'>;actions:NativeAction[];deadline?:string}
const dateOf=(day:string)=>new Date(day+'T12:00:00Z');
const weekend=(day:string)=>[0,6].includes(dateOf(day).getUTCDay());
const weekday=new Intl.DateTimeFormat('fr-FR',{weekday:'narrow',timeZone:'UTC'});

/** JSX and class vocabulary from the user's Lovable v2, backed by real Yjs ranges. */
export function PlanningTimeline({groups,month,onMonth,onAction,onSource,canWrite,controls,loading=false,unavailable=false}:{groups:TimelineGroup[];month:string;onMonth:(value:string)=>void;onAction:(action:NativeAction)=>void;onSource?:(sourceId:string)=>void;canWrite:boolean;controls?:ReactNode;loading?:boolean;unavailable?:boolean}){
 const window=monthWindow(month),style={gridTemplateColumns:`repeat(${window.days.length}, minmax(28px, 1fr))`};
 const label=new Intl.DateTimeFormat('fr-FR',{month:'long',year:'numeric',timeZone:'UTC'}).format(dateOf(window.start));
 const scheduledGroups=groups.map(group=>({...group,actions:group.actions.filter(action=>timelineAction(action))}));
 const overview=timelineOverview(groups,month);
 const cells=()=>window.days.map(day=><span key={day} className={`gantt-cell ${weekend(day)?'weekend':''}`} aria-hidden="true"/>);
 return <>
  <div className="planning-month-toolbar"><div className="month-navigation"><Button variant="ghost" size="icon" aria-label="Mois précédent" onClick={()=>onMonth(shiftMonth(month,-1))}><ChevronLeft/></Button><h3 aria-live="polite">{label}</h3><Button variant="ghost" size="icon" aria-label="Mois suivant" onClick={()=>onMonth(shiftMonth(month,1))}><ChevronRight/></Button><Button variant="ghost" size="sm" onClick={()=>onMonth(dayFromGanttDate(new Date()).slice(0,7))}>Aujourd’hui</Button></div>{controls}<div className="gantt-legend"><span><i className="project-dot"/>Période d’action</span><span><Diamond size={12}/>Échéance ou date du dossier</span></div></div>
  {overview.hasDates&&<div className="gantt-scroll" role="region" aria-label={`Planning de ${label}`} tabIndex={0}><div className="gantt-board">
   <div className="gantt-line gantt-heading"><div className="gantt-label">CHANTIER / ACTION</div><div className="gantt-track" style={style}>{window.days.map(day=><span key={day} className={`gantt-day ${weekend(day)?'weekend':''}`}><small>{weekday.format(dateOf(day))}</small>{Number(day.slice(-2))}</span>)}</div></div>
   {scheduledGroups.filter(group=>group.actions.length||planningMilestones(group.project,group.deadline).length).map(({project,actions,deadline})=><div className="gantt-project" key={project.id} data-timeline-project={project.id}>
    <div className="gantt-line project-line"><div className="gantt-label"><a href={`#/chantiers/${encodeURIComponent(project.id)}?view=planning`}>{project.name}</a><small>{project.reference}</small></div><div className="gantt-track" style={style}>{cells()}{planningMilestones(project,deadline).map(item=>{const placement=timelinePlacement(item.date,item.date,window.start,window.days.length),description=`${item.label}${item.confirmed?' confirmée':''} : ${formatDate(item.date)}`;return placement?(item.sourceId&&onSource?<button key={item.id} className="gantt-milestone" style={{gridColumn:placement.column,gridRow:1}} title={description} aria-label={`${description} — ouvrir la source`} onClick={()=>onSource(item.sourceId!)}><Diamond size={17}/></button>:<span key={item.id} className="gantt-milestone structured-deadline" style={{gridColumn:placement.column,gridRow:1}} role="img" title={description} aria-label={description}><Diamond size={17}/></span>):null;})}</div></div>
    {actions.map(action=>{const entry=timelineAction(action)!,placement=timelinePlacement(entry.start,entry.end,window.start,window.days.length);return <div className="gantt-line" key={action.id} data-timeline-row={action.id}><div className="gantt-label gantt-action-label"><Button variant="ghost" className="gantt-action-name" onClick={()=>onAction(action)}>{action.title}</Button><small>{action.owner||'À attribuer'} · {action.status||'Statut non renseigné'}</small>{entry.kind==='deadline'&&<small>Échéance : {formatDate(action.due)} · Début non renseigné</small>}</div><div className="gantt-track" style={style}>{cells()}{placement&&(entry.kind==='deadline'?<button className="gantt-milestone action-deadline" style={{gridColumn:placement.column,gridRow:1}} onClick={()=>onAction(action)} aria-label={`Échéance de ${action.title} : ${formatDate(action.due)} ; début non renseigné`}><Diamond size={17}/></button>:<button className={`gantt-bar ${action.status==='Terminé'?'completed':action.status==='En attente'?'waiting':''}`} style={{gridColumn:`${placement.column} / span ${placement.span}`,gridRow:1}} onClick={()=>onAction(action)} title={`${action.title} : ${formatDate(action.start||'')} — ${formatDate(action.due)}`} aria-label={`${canWrite?'Planifier':'Consulter'} ${action.title}, du ${formatDate(action.start||'')} au ${formatDate(action.due)}`}><span>{placement.span>2?action.title:''}</span></button>)}</div></div>;})}
   </div>)}
   {!groups.length&&<div className="empty">Aucun chantier pour cette sélection.</div>}
  </div></div>}
  {!overview.hasDates&&!loading&&(unavailable?<p className="planning-status">Le chargement des dates est incomplet. Actualisez le planning pour vérifier leur disponibilité.</p>:<div className="planning-empty"><div><h3>Aucune date à afficher</h3><p>{groups.length?'Les actions datées et les échéances renseignées apparaîtront ici. Une date de demande ne définit pas le début d’une action.':'Aucun dossier pour cette sélection.'}</p>{canWrite&&groups.length>0&&<a href="#/actions">Créer une action</a>}</div></div>)}
  {overview.hasDates&&overview.visibleCount===0&&overview.nearestMonth&&<p className="planning-status">Des dates existent en dehors du mois affiché. <Button variant="link" size="sm" onClick={()=>onMonth(overview.nearestMonth!)}>Voir la période la plus proche</Button></p>}
 </>;
}
