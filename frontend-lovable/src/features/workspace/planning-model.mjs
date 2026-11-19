export function validDay(value){
 return typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value;
}
export function dayFromGanttDate(value){
 if(!(value instanceof Date)||!Number.isFinite(value.getTime()))return '';
 return `${String(value.getFullYear()).padStart(4,'0')}-${String(value.getMonth()+1).padStart(2,'0')}-${String(value.getDate()).padStart(2,'0')}`;
}
export function scheduleOf(action){
 if(!validDay(action.start)||!validDay(action.due)||action.start>action.due)return null;
 if((Date.parse(action.due)-Date.parse(action.start))/86400000>3653)return null;
 return {start:action.start,end:action.due};
}
export function schedulePatch(start,end,progress){
 if(!validDay(start)||!validDay(end))throw Error('Renseignez un début et une fin valides.');
 if(start>end)throw Error('La fin doit être le même jour ou après le début.');
 if(!scheduleOf({start,due:end}))throw Error('Cette durée dépasse les dix ans affichables dans la frise.');
 return {startDate:start,dueDate:end,progress:progressValue(progress)};
}
function progressValue(progress){
 const value=progress===''?'':Number(progress);
 if(value!==''&&(!Number.isInteger(value)||value<0||value>100))throw Error('L’avancement doit être un entier de 0 à 100.');
 return value;
}
export function scheduleFormPatch(action,start,end,progress,owner,status){
 if(start&&!validDay(start))throw Error('Renseignez une date de début valide ou laissez ce champ vide.');
 if(end&&!validDay(end))throw Error('Renseignez une échéance valide ou laissez ce champ vide.');
 const patch=start&&end?schedulePatch(start,end,progress):{startDate:start,dueDate:end,progress:progressValue(progress)};
 return {...patch,...(owner!==action.owner?{owner}:{}),...(status!==action.status?{status}:{})};
}
export function planningActionGroups(items,projects){
 const labels=new Map(projects.map(project=>[project.id,project.title]));
 const groups=new Map();
 for(const action of items){
  if(!groups.has(action.projectId))groups.set(action.projectId,{id:action.projectId,label:labels.get(action.projectId)||'Chantier non disponible',items:[]});
  groups.get(action.projectId).items.push(action);
 }
 return [...groups.values()];
}
export function planningOwnerChoices(_members,items,current='',projectId=''){
 if(!projectId)return [];
 return [...new Set([...items.filter(action=>action.projectId===projectId).map(action=>action.owner),current].filter(value=>typeof value==='string'&&value.trim()))];
}
export function planningConsistencyWarning(status,progress){
 if(progress==='')return '';
 const value=Number(progress);if(!Number.isInteger(value)||value<0||value>100)return '';
 if(status==='Terminé'&&value<100)return `Le statut est « Terminé » avec un avancement de ${value} %. Vérifiez ces deux informations ; elles ne se modifient pas automatiquement.`;
 if(status==='À faire'&&value>0)return `L’action est « À faire » avec un avancement de ${value} %. Vérifiez si son statut doit évoluer.`;
 if(status==='En cours'&&value===100)return 'L’avancement est de 100 % alors que l’action est « En cours ». Vérifiez si elle est terminée.';
 return '';
}
export function planningFormDirty(action,start,end,progress,owner,status){
 if(!action)return false;
 return (action.start||'')!==start||(action.due||'')!==end||(typeof action.progress==='number'?String(action.progress):'')!==progress||action.owner!==owner||action.status!==status;
}
export function monthWindow(month){
 if(typeof month!=='string'||!/^\d{4}-\d{2}$/.test(month)||!validDay(month+'-01'))throw Error('Choisissez un mois valide.');
 const [year,index]=month.split('-').map(Number),count=new Date(Date.UTC(year,index,0)).getUTCDate();
 return {start:month+'-01',days:Array.from({length:count},(_,day)=>`${month}-${String(day+1).padStart(2,'0')}`)};
}
export function shiftMonth(month,offset){
 monthWindow(month);
 const date=new Date(month+'-01T12:00:00Z');date.setUTCMonth(date.getUTCMonth()+offset);
 return date.toISOString().slice(0,7);
}
/** Lovable v2 placement, using validated UTC calendar days and no inferred range. */
export function timelinePlacement(start,end,windowStart,days){
 if(!validDay(start)||!validDay(end)||!validDay(windowStart)||start>end||!Number.isInteger(days)||days<1)return null;
 const first=(Date.parse(start)-Date.parse(windowStart))/86400000,last=(Date.parse(end)-Date.parse(windowStart))/86400000;
 if(last<0||first>=days)return null;
 return {column:Math.max(0,first)+1,span:Math.min(days-1,last)-Math.max(0,first)+1};
}
const escapeSvgText=value=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
export function ganttTasks(rows){
 const actions=new Map(),tasks=[];
 for(const action of rows){
  const schedule=scheduleOf(action);if(!schedule)continue;
  const id=`action-${tasks.length}`;actions.set(id,action);
  const known=Number.isInteger(action.progress)&&action.progress>=0&&action.progress<=100;
  tasks.push({id,name:escapeSvgText(action.title),start:schedule.start,end:schedule.end,progress:known?action.progress:0,dependencies:[],custom_class:['planning-task',known?'':'progress-unknown',action.status==='Terminé'?'task-complete':''].filter(Boolean).join(' ')});
 }
 return {tasks,actions};
}
export function calendarEventsOf(value,projectId){
 const rows=Array.isArray(value)?value:Array.isArray(value?.items)?value.items:[];
 return rows.filter(item=>item&&item.project_id===projectId&&typeof item.id==='string'&&typeof item.title==='string'&&item.title.length<=2000&&typeof item.start==='string'&&typeof item.end==='string'&&Number.isFinite(Date.parse(item.start))&&Number.isFinite(Date.parse(item.end))&&Date.parse(item.end)>=Date.parse(item.start)).map(item=>({id:item.id,title:item.title,start:item.start,end:item.end,all_day:item.all_day===true,calendar_name:typeof item.calendar_name==='string'?item.calendar_name:'Agenda',project_id:projectId,status:typeof item.status==='string'?item.status:'',source_url:typeof item.source_url==='string'?item.source_url:''})).sort((a,b)=>Date.parse(a.start)-Date.parse(b.start));
}
export function safeCalendarUrl(value){
 try{const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password?url.href:null;}catch{return null;}
}

/** A deadline is a point; it never supplies a missing start date. */
export function timelineAction(action){
 const range=scheduleOf(action);if(range)return {kind:'range',...range};
 return !action.start&&validDay(action.due)?{kind:'deadline',start:action.due,end:action.due}:null;
}
export function planningMilestones(project,deadline){
 const override=project?.properties?.values?.deadline,hasOverride=typeof override==='string';
 if(hasOverride)deadline=override;
 const dates=(Array.isArray(project?.facts)?project.facts:[])
  .filter(item=>item.status==='accepted'&&item.kind==='date'&&validDay(item.value)&&['delivery_date','deadline','acceptance_date'].includes(item.field)&&!(hasOverride&&item.field==='deadline'))
  .map(item=>({id:item.id,label:item.label,date:item.value,sourceId:item.source_id||undefined,confirmed:true}));
 if(validDay(deadline)&&!dates.some(item=>item.date===deadline&&item.label==='Échéance du dossier')){
  const sameFact=!hasOverride&&(project?.facts||[]).some(item=>item.status==='accepted'&&item.field==='deadline'&&item.value===deadline);
  if(!sameFact)dates.push({id:'structured-deadline',label:'Échéance du dossier',date:deadline,sourceId:undefined,confirmed:false});
 }
 return dates.sort((a,b)=>a.date.localeCompare(b.date));
}
export function timelineOverview(groups,month){
 const window=monthWindow(month),last=window.days.at(-1),entries=[];
 for(const group of groups){
  for(const action of group.actions){const entry=timelineAction(action);if(entry)entries.push(entry);}
  for(const point of planningMilestones(group.project,group.deadline))entries.push({kind:'milestone',start:point.date,end:point.date});
 }
 const visibleCount=entries.filter(entry=>entry.start<=last&&entry.end>=window.start).length;
 const nearest=[...entries].sort((a,b)=>{
  const distance=entry=>entry.end<window.start?Date.parse(window.start)-Date.parse(entry.end):entry.start>last?Date.parse(entry.start)-Date.parse(last):0;
  return distance(a)-distance(b)||a.start.localeCompare(b.start);
 })[0];
 return {hasDates:entries.length>0,visibleCount,nearestMonth:nearest?(nearest.end<window.start?nearest.end:nearest.start).slice(0,7):null};
}
export async function loadPlanningProjects(ids,read){
 const projects=[];let failed=0;
 for(let offset=0;offset<ids.length;offset+=6){
  const batch=await Promise.allSettled(ids.slice(offset,offset+6).map(read));
  for(const result of batch){if(result.status==='fulfilled')projects.push(result.value);else failed++;}
 }
 return {projects,failed};
}
