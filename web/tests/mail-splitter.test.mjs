import test from 'node:test';
import assert from 'node:assert/strict';
import {mailPaneBounds,fitMailWidth,readMailWidth} from '../mail-splitter.js';

test('both mail panes must retain enough usable space before resizing is enabled',()=>{
 for(const width of [0,300,559,NaN,Infinity,-10])assert.equal(mailPaneBounds(width),null);
 assert.deepEqual(mailPaneBounds(560),{min:240,max:240});
 assert.deepEqual(mailPaneBounds(800),{min:240,max:480});
 assert.deepEqual(mailPaneBounds(1800),{min:240,max:720});
});

test('saved widths accept only a bounded plain integer, never arbitrary browser storage',()=>{
 for(const value of [null,'','239','721','999999','310px','3e2','310.5','<script>','0310','Infinity','310 ',310])assert.equal(readMailWidth(value),null);
 assert.equal(readMailWidth('240'),240);assert.equal(readMailWidth('310'),310);assert.equal(readMailWidth('720'),720);
});

test('dragging either edge cannot collapse the list or its reading pane',()=>{
 for(const available of [560,575,800,1100,1600]){
  const bounds=mailPaneBounds(available);
  for(const requested of [-10000,0,240,310,420,720,10000,NaN]){
   const result=fitMailWidth(requested,bounds);
   assert(result>=240);assert(result<=720);assert(available-result>=320);
  }
 }
});
