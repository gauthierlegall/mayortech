import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveSummaryDestination} from './summary-redirect.mjs';

test('former summary index returns to projects without fetching summaries',async()=>{
 let calls=0;
 assert.equal(await resolveSummaryDestination({summary:async()=>{calls++;}},undefined,['p1']),'#/');
 assert.equal(calls,0);
});
test('a legacy summary loads its owning project and opens the existing project page',async()=>{
 const ids=[];
 const target=await resolveSummaryDestination({summary:async id=>{ids.push(id);return {id,project_id:'project-1'};}},'summary-1',['project-1']);
 assert.equal(target,'#/chantiers/project-1?view=page');assert.deepEqual(ids,['summary-1']);
});
test('an inaccessible summary or revoked owning project returns to authorized projects',async()=>{
 assert.equal(await resolveSummaryDestination({summary:async()=>{throw Error('private failure details');}},'s1',['p1']),'#/');
 assert.equal(await resolveSummaryDestination({summary:async()=>({id:'s1',project_id:'revoked'})},'s1',['p1']),'#/');
});
test('a mismatched summary cannot redirect to a different project',async()=>{
 assert.equal(await resolveSummaryDestination({summary:async()=>({id:'other',project_id:'p1'})},'s1',['p1']),'#/');
 assert.equal(await resolveSummaryDestination({summary:async()=>({id:'s1',project_id:42})},'s1',['p1']),'#/');
});
test('malformed legacy identifiers do not reach the API',async()=>{
 let calls=0;const api={summary:async()=>{calls++;}};
 for(const id of ['',null,'../outside','https://elsewhere.invalid','x\n', 'x'.repeat(201)])assert.equal(await resolveSummaryDestination(api,id,['p1']),'#/');
 assert.equal(calls,0);
});
test('unsafe project identifiers never become a navigation destination',async()=>{
 for(const project_id of ['../outside','https://elsewhere.invalid','..','p/1'])assert.equal(await resolveSummaryDestination({summary:async()=>({id:'s1',project_id})},'s1',[project_id]),'#/');
});
