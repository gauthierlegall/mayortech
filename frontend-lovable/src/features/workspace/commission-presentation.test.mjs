import test from 'node:test';
import assert from 'node:assert/strict';
import {presentationForCommission,projectViewForCommission,orderPropertyFields} from './commission-presentation.mjs';

test('each commission opens its working view and keeps dossiers available',()=>{
  for(const [id,view] of [['commission-1','arbitration'],['commission-2','campaigns'],['commission-3','projects'],['commission-4','agenda']]){
    assert.equal(projectViewForCommission(id,null),view);
    assert.equal(projectViewForCommission(id,'projects'),'projects');
    assert.ok(presentationForCommission(id).views.includes('projects'));
  }
});
test('stale URLs cannot select the map or finance view in another profile',()=>{
  assert.equal(projectViewForCommission('commission-3','map'),'map');
  assert.equal(projectViewForCommission('commission-4','map'),'agenda');
  assert.equal(projectViewForCommission('commission-2','arbitration'),'campaigns');
  for(const id of ['all','unknown','']){
    assert.equal(projectViewForCommission(id,'map'),'projects');
    assert.equal(projectViewForCommission(id,'arbitration'),'projects');
  }
});
test('property emphasis retains every original field exactly once without mutating input',()=>{
  const keys=['name','category','status','priority','request_date','deadline','requester','service_owner','contractor','location','estimated_cost','actual_cost','notes','observation','future_field'];
  const fields=keys.map(key=>({key,label:key}));
  for(const id of ['commission-1','commission-2','commission-3','commission-4','all','unknown']){
    const ordered=orderPropertyFields(fields,id);
    assert.deepEqual(ordered.map(field=>field.key).toSorted(),keys.toSorted());
    assert.equal(new Set(ordered).size,fields.length);
    assert.deepEqual(fields.map(field=>field.key),keys);
  }
  assert.ok(orderPropertyFields(fields,'commission-1').findIndex(f=>f.key==='estimated_cost')<4);
  assert.ok(orderPropertyFields(fields,'commission-4').findIndex(f=>f.key==='deadline')<4);
  assert.ok(orderPropertyFields(fields,'commission-2').findIndex(f=>f.key==='service_owner')<5);
  assert.deepEqual(orderPropertyFields(fields,'all'),fields);
});
