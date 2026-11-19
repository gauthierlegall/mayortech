import test from 'node:test';
import assert from 'node:assert/strict';
let model={};try{model=await import('./assistant-widget-model.mjs');}catch{}

test('popup stays above mobile navigation and within a 320 or 390 viewport',()=>{
 for(const height of [760,844]){
  const result=model.widgetViewport?.({layoutHeight:height,visibleHeight:height,offsetTop:0,mobile:true});
  assert.ok(result);
  assert.ok(result.bottom>=140);
  assert.ok(height-result.bottom-result.height>=12);
  assert.equal(result.keyboard,false);
 }
});

test('a visible virtual keyboard keeps the popup composer above its edge',()=>{
 const result=model.widgetViewport?.({layoutHeight:844,visibleHeight:390,offsetTop:0,mobile:true});
 assert.ok(result);
 assert.equal(result.keyboard,true);
 assert.equal(result.bottom,462);
 assert.ok(844-result.bottom-result.height>=12);
});

test('initial thread selection only resumes a thread visible in the returned scope',()=>{
 const threads=[{id:'a',project_id:'p'},{id:'b',project_id:null},{id:'c',project_id:'q'}];
 assert.equal(model.initialThread?.(threads,'p','c')?.id,'a');
 assert.equal(model.initialThread?.(threads,undefined,'b')?.id,'b');
 assert.equal(model.initialThread?.(threads,'unknown','c'),null);
 assert.equal(model.initialThread?.([],undefined,'private-invisible'),null);
});

test('draft namespaces change on logout, actor changes and tenant changes',()=>{
 const one={authenticated:true,actor:{tenant_id:'town',actor_id:'one'}};
 assert.notEqual(model.assistantSessionIdentity(one),model.assistantSessionIdentity({authenticated:false}));
 assert.notEqual(model.assistantSessionIdentity(one),model.assistantSessionIdentity({...one,actor:{...one.actor,actor_id:'two'}}));
 assert.notEqual(model.assistantSessionIdentity(one),model.assistantSessionIdentity({...one,actor:{...one.actor,tenant_id:'other'}}));
});
