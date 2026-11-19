import assert from 'node:assert/strict';
import test from 'node:test';
import * as planning from './planning-model.mjs';

test('a known deadline is a point, never an invented action duration',()=>{
 const action={id:'qa-action',due:'2027-02-12'};
 assert.deepEqual(planning.timelineAction(action),{kind:'deadline',start:'2027-02-12',end:'2027-02-12'});
 assert.equal(action.start,undefined);assert.equal(planning.scheduleOf(action),null);
 assert.equal(planning.timelineAction({due:'2027-02-30'}),null);
});

test('only structured deadlines and accepted date facts become dossier milestones',()=>{
 const project={facts:[{id:'accepted',kind:'date',field:'delivery_date',value:'2027-03-04',status:'accepted',label:'Livraison',source_id:'qa-source'},{id:'pending',kind:'date',field:'deadline',value:'2027-04-10',status:'pending'}],requestDate:'2026-01-01',description:'Une date narrative 2028-01-01'};
 const dates=planning.planningMilestones(project,'2027-02-12');
 assert.deepEqual(dates.map(item=>item.date),['2027-02-12','2027-03-04']);
 assert.equal(dates[0].label,'Échéance du dossier');assert.equal(dates[0].confirmed,false);
 assert.equal(dates[1].sourceId,'qa-source');
 assert.deepEqual(planning.planningMilestones({facts:[],requestDate:'2026-01-01'}),[]);
});

test('an explicit deadline override, including a clear, never resurrects an older fact',()=>{
 const fact={id:'old',label:'Ancienne échéance',kind:'date',field:'deadline',value:'2027-01-01',status:'accepted'};
 assert.deepEqual(planning.planningMilestones({facts:[fact],properties:{values:{deadline:''}}},'2027-01-01'),[]);
 assert.deepEqual(planning.planningMilestones({facts:[fact],properties:{values:{deadline:'2027-05-12'}}},'2027-01-01').map(item=>item.date),['2027-05-12']);
});

test('a deadline-only dossier counts as visible data and offers the nearest month when outside',()=>{
 const groups=[{project:{facts:[]},actions:[],deadline:'2027-02-12'}];
 assert.equal(planning.timelineOverview(groups,'2027-02').visibleCount,1);
 assert.equal(planning.timelineOverview(groups,'2026-11').nearestMonth,'2027-02');
 assert.equal(planning.timelineOverview(groups,'2026-11').hasDates,true);
 assert.equal(planning.timelineOverview([],'2026-11').hasDates,false);
});

test('out-of-window actions offer the nearest endpoint without moving saved dates',()=>{
 const actions=[{start:'2020-01-01',due:'2020-01-02'},{start:'2027-02-03',due:'2027-02-05'}];
 const result=planning.timelineOverview([{project:{facts:[]},actions}],'2026-11');
 assert.equal(result.visibleCount,0);assert.equal(result.nearestMonth,'2027-02');
 assert.equal(actions[0].start,'2020-01-01');
});

test('partial dossier loading retains successes and limits concurrent work',async()=>{
 let active=0,maximum=0;
 const result=await planning.loadPlanningProjects(Array.from({length:15},(_,index)=>String(index)),async id=>{
  active++;maximum=Math.max(maximum,active);await Promise.resolve();active--;
  if(id==='2')throw Error('fixture failure');return {id};
 });
 assert.equal(result.projects.length,14);assert.equal(result.failed,1);assert.ok(maximum<=6);
 assert.deepEqual(await planning.loadPlanningProjects([],()=>{throw Error('must not run');}),{projects:[],failed:0});
});
