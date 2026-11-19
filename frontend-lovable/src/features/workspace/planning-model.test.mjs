import test from 'node:test';
import assert from 'node:assert/strict';
import {dayFromGanttDate,validDay,scheduleOf,schedulePatch,scheduleFormPatch,ganttTasks,calendarEventsOf,safeCalendarUrl,monthWindow,shiftMonth,timelinePlacement} from './planning-model.mjs';
import * as planning from './planning-model.mjs';

test('an action can keep only its known deadline when editing its follow-up',()=>{
 assert.deepEqual(scheduleFormPatch({owner:'',status:'À faire'},'','2026-11-20','','Service scolaire','En attente'),{startDate:'',dueDate:'2026-11-20',progress:'',owner:'Service scolaire',status:'En attente'});
 assert.deepEqual(scheduleFormPatch({owner:'',status:'À faire'},'','','','','À faire'),{startDate:'',dueDate:'',progress:''});
 assert.deepEqual(scheduleFormPatch({owner:'',status:'À faire'},'2026-11-16','','0','','À faire'),{startDate:'2026-11-16',dueDate:'',progress:0});
});

test('a partial schedule still rejects invalid dates without inventing a range',()=>{
 const action={owner:'',status:'À faire'};
 for(const [start,end] of [['2026-02-30',''],['','2026-13-01'],['2026-11-21','2026-11-20']])assert.throws(()=>scheduleFormPatch(action,start,end,'','','À faire'));
});

test('removing a start preserves the deadline and other explicit edits in one patch',()=>{
 const action={owner:'Ancien responsable',status:'En cours'};
 assert.deepEqual(scheduleFormPatch(action,'','2026-11-25','40','Service travaux','En attente'),{startDate:'',dueDate:'2026-11-25',progress:40,owner:'Service travaux',status:'En attente'});
});

test('global choices keep equally named actions distinguishable by their real project',()=>{
 const groups=planning.planningActionGroups?.([{id:'same',projectId:'p',title:'Visite'},{id:'same',projectId:'q',title:'Visite'}],[{id:'p',title:'École'},{id:'q',title:'Gymnase'}])??[];
 assert.deepEqual(groups.map(group=>({id:group.id,label:group.label,values:group.items.map(action=>`${action.projectId}:${action.id}`)})),[{id:'p',label:'École',values:['p:same']},{id:'q',label:'Gymnase',values:['q:same']}]);
});

test('responsible suggestions include saved non-member owners without assigning one automatically',()=>{
 const action={projectId:'ajoncs',owner:'',status:'À faire'};
 const owners=planning.planningOwnerChoices(['Opérateur de cet espace'],[{projectId:'ajoncs',owner:'Entreprise extérieure'},{projectId:'ajoncs',owner:'Luc Martin'},action],'Responsable historique','ajoncs');
 assert.deepEqual(owners,['Entreprise extérieure','Luc Martin','Responsable historique']);
 assert.equal(action.owner,'');
 assert.equal('owner' in scheduleFormPatch(action,'','2026-11-20','','','À faire'),false);
 assert.equal(scheduleFormPatch(action,'','2026-11-20','','Entreprise saisie libre','À faire').owner,'Entreprise saisie libre');
});

test('responsible suggestions stay within Ajoncs or Chenes when the global planning changes project',()=>{
 const actions=[{projectId:'ajoncs',owner:'Luc Martin'},{projectId:'chenes',owner:'Nora Le Roux'},{projectId:'ajoncs',owner:'Entreprise des Ajoncs'},{projectId:'chenes',owner:'Service des Chênes'},{projectId:'ajoncs',owner:'Luc Martin'}];
 assert.deepEqual(planning.planningOwnerChoices(['Opérateur de cet espace'],actions,'Responsable historique des Ajoncs','ajoncs'),['Luc Martin','Entreprise des Ajoncs','Responsable historique des Ajoncs']);
 assert.deepEqual(planning.planningOwnerChoices(['Opérateur de cet espace'],actions,'','chenes'),['Nora Le Roux','Service des Chênes']);
 assert.deepEqual(planning.planningOwnerChoices(['Opérateur de cet espace'],actions,'',''),[]);
 assert.deepEqual(planning.planningOwnerChoices(['Opérateur de cet espace'],actions,'','sans-action'),[]);
});

test('contradictory known status and progress get a warning while unknown and custom values remain independent',()=>{
 assert.equal((planning.planningConsistencyWarning?.('Terminé','20')??'').length>0,true);
 assert.equal((planning.planningConsistencyWarning?.('À faire','60')??'').length>0,true);
 assert.equal(planning.planningConsistencyWarning?.('Terminé','')??'','');
 assert.equal(planning.planningConsistencyWarning?.('Statut personnalisé','30')??'','');
 const patch=scheduleFormPatch({owner:'',status:'En cours'},'','','20','','Terminé');
 assert.equal(patch.status,'Terminé');assert.equal(patch.progress,20);
});

test('switching actions can detect unsaved fields including unknown versus explicit zero',()=>{
 const action={owner:'Service travaux',status:'À faire',start:'',due:'2026-11-20'};
 assert.equal(planning.planningFormDirty?.(action,'','2026-11-20','0','Service travaux','À faire')??false,true);
 assert.equal(planning.planningFormDirty?.(action,'','2026-11-20','','Service travaux','À faire')??true,false);
 assert.equal(planning.planningFormDirty?.(action,'2026-11-16','2026-11-20','','Service travaux','À faire')??false,true);
});

test('the shared schedule form updates canonical owner/status only when explicitly changed',()=>{
 const action={owner:'Responsable historique',status:'Statut personnalisé conservé'};
 const unchanged=scheduleFormPatch(action,'2026-11-16','2026-11-20','','Responsable historique','Statut personnalisé conservé');
 assert.equal('owner' in unchanged,false);assert.equal('status' in unchanged,false);
 assert.deepEqual(scheduleFormPatch(action,'2026-11-16','2026-11-20','0','Membre réel','En cours'),{startDate:'2026-11-16',dueDate:'2026-11-20',progress:0,owner:'Membre réel',status:'En cours'});
 assert.equal(scheduleFormPatch(action,'2026-11-16','2026-11-20','','','En attente').owner,'');
});

test('a real monthly window follows leap years and year boundaries',()=>{
 assert.equal(monthWindow('2028-02').days.length,29);
 assert.equal(monthWindow('2026-11').days.length,30);
 assert.equal(monthWindow('2026-11').days[0],'2026-11-01');
 assert.equal(shiftMonth('2026-01',-1),'2025-12');
 assert.equal(shiftMonth('2026-12',1),'2027-01');
 assert.throws(()=>monthWindow('2026-13'));
});

test('Lovable monthly placement clips real dates at month boundaries without inventing starts',()=>{
 assert.deepEqual(timelinePlacement('2026-10-28','2026-11-03','2026-11-01',30),{column:1,span:3});
 assert.deepEqual(timelinePlacement('2026-11-29','2026-12-03','2026-11-01',30),{column:29,span:2});
 assert.deepEqual(timelinePlacement('2026-11-20','2026-11-20','2026-11-01',30),{column:20,span:1});
 assert.equal(timelinePlacement('','2026-11-20','2026-11-01',30),null);
 assert.equal(timelinePlacement('2026-11-21','2026-11-20','2026-11-01',30),null);
 assert.equal(timelinePlacement('2026-12-01','2026-12-02','2026-11-01',30),null);
});

test('calendar days reject impossible dates and never infer a start from a deadline',()=>{
 assert.equal(validDay('2026-02-30'),false);
 assert.equal(validDay('2028-02-29'),true);
 assert.equal(validDay('2026-11-20T00:00:00Z'),false);
 assert.equal(scheduleOf({id:'a',due:'2026-11-20'}),null);
 assert.equal(scheduleOf({start:'2026-11-21',due:'2026-11-20'}),null);
 assert.deepEqual(scheduleOf({start:'2026-11-20',due:'2026-11-20'}),{start:'2026-11-20',end:'2026-11-20'});
});
test('schedule edits preserve an unknown progress and explicit zero or clear',()=>{
 assert.deepEqual(schedulePatch('2026-11-16','2026-11-17',''),{startDate:'2026-11-16',dueDate:'2026-11-17',progress:''});
 assert.equal(schedulePatch('2026-11-16','2026-11-17','0').progress,0);
 assert.equal(schedulePatch('2026-11-16','2026-11-17','100').progress,100);
 for(const value of ['101','-1','1.5','NaN'])assert.throws(()=>schedulePatch('2026-11-16','2026-11-17',value));
 assert.throws(()=>schedulePatch('2026-11-21','2026-11-20','50'));
});
test('Frappe dates keep the local business day across a DST boundary',()=>{
 const previous=process.env.TZ;process.env.TZ='Europe/Paris';
 try{
  const localMidnight=new Date(2026,2,30,0,0,0);
  assert.equal(dayFromGanttDate(localMidnight),'2026-03-30');
  assert.equal(dayFromGanttDate(new Date('invalid')),'');
 }finally{if(previous===undefined)delete process.env.TZ;else process.env.TZ=previous;}
});
test('gantt labels are escaped for the upstream SVG innerHTML sink, not treated as markup',()=>{
 const rows=[{id:'human<id>',title:'<image href="x" onerror="alert(1)">',start:'2026-11-16',due:'2026-11-17',progress:0},{id:'without-start',title:'À dater',due:'2026-11-20'}];
 const mapped=ganttTasks(rows);
 assert.equal(mapped.tasks.length,1);
 assert.equal(mapped.tasks[0].id,'action-0');
 assert.equal(mapped.tasks[0].name.includes('<'),false);
 assert.equal(mapped.actions.get('action-0'),rows[0]);
 assert.equal(mapped.tasks[0].progress,0);
 assert.equal(mapped.tasks[0].custom_class.includes('progress-unknown'),false);
});
test('missing progress is visually indeterminate, distinct from explicitly zero',()=>{
 const {tasks}=ganttTasks([{id:'a',title:'Visite',start:'2026-11-20',due:'2026-11-20'}]);
 assert.match(tasks[0].custom_class,/progress-unknown/);
 assert.equal('progress' in tasks[0],true);
});
test('calendar events are only accepted for the requested project, with real endpoints',()=>{
 const events=calendarEventsOf({items:[{id:'own',project_id:'p',title:'Visite',start:'2026-11-20T09:00:00+01:00',end:'2026-11-20T10:00:00+01:00',calendar_name:'Travaux',all_day:false,status:'tentative'},{id:'other',project_id:'q',title:'Hors périmètre',start:'2026-11-20',end:'2026-11-21'},{id:'broken',project_id:'p',start:'invalid',end:'2026-11-20'}]},'p');
 assert.equal(events.length,1);assert.equal(events[0].id,'own');assert.equal(events[0].status,'tentative');
});
test('calendar source links do not permit scripts or embedded credentials',()=>{
 assert.equal(safeCalendarUrl('javascript:alert(1)'),null);
 assert.equal(safeCalendarUrl('https://user:secret@agenda.example.invalid/'),null);
 assert.equal(safeCalendarUrl('https://agenda.example.invalid/event/1'),'https://agenda.example.invalid/event/1');
});
