import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

test('leaving and reopening a Gantt does not retain a document handler or detached chart',async()=>{
 const path=process.env.GANTT_TEST_UPSTREAM?'../../../node_modules/frappe-gantt/src/index.js':'../../vendor/frappe-gantt/index.js';
 const source=(await readFile(new URL(path,import.meta.url),'utf8')).replace(/^import .*;\r?$/gm,'').replace('export default class Gantt','globalThis.Gantt=class Gantt');
 const listeners=new Set();
 const context={DEFAULT_VIEW_MODES:[],DEFAULT_OPTIONS:{},document:{addEventListener:(type,handler)=>listeners.add(handler),removeEventListener:(type,handler)=>listeners.delete(handler)},$:{on:()=>{}}};
 vm.runInNewContext(source,context);
 for(let visit=0;visit<20;visit++){
  let removed=0;const chart=Object.create(context.Gantt.prototype);
  Object.assign(chart,{$svg:{remove:()=>removed++},$container:{remove:()=>removed++,querySelector:()=>null},config:{ignored_positions:[]},options:{},tasks:[{}],bars:[{}]});
  chart.bind_bar_events();assert.equal(listeners.size,1);
  chart.destroy();assert.equal(listeners.size,0);assert.equal(removed,2);assert.equal(chart.tasks.length,0);assert.equal(chart.bars.length,0);
 }
});
