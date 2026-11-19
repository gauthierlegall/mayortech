import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeActionPatch,normalizeActionImports} from '../src/native-commands.mjs';
test('an action patch preserves explicit clears and rejects fields that can change provenance',()=>{
 assert.deepEqual(normalizeActionPatch({description:'',owner:' Marie ',dueDate:'',priority:'Haute',status:'En cours'}),{description:'',owner:'Marie',dueDate:'',priority:'Haute',status:'En cours'});
 for(const patch of [{sourceUrl:'#/mail/other'},{sourceKey:'replace'},{title:''},{dueDate:'2026-02-30'},{status:'made-up'}])assert.throws(()=>normalizeActionPatch(patch));
});
test('new action imports keep operational priority as plain bounded text',()=>{
 assert.equal(normalizeActionImports([{sourceKey:'manual',title:'Accès',priority:'Haute'}])[0].priority,'Haute');
 assert.throws(()=>normalizeActionPatch({description:'x'.repeat(4001)}));
});
test('action patches accept a custom status only when the target database defines it',()=>{
 assert.deepEqual(normalizeActionPatch({title:'Accès côté cour',status:'Bloqué'},['À faire','Bloqué']),{title:'Accès côté cour',status:'Bloqué'});
 assert.throws(()=>normalizeActionPatch({status:'Bloqué'},['À faire','Terminé']));
 assert.throws(()=>normalizeActionPatch({status:'Inventé'},['À faire','Bloqué']));
});
test('planning dates are explicit, bounded calendar dates and ordered without invented durations',()=>{
 assert.deepEqual(normalizeActionPatch({startDate:'2026-11-16',dueDate:'2026-11-17',progress:25}),{progress:25,startDate:'2026-11-16',dueDate:'2026-11-17'});
 assert.deepEqual(normalizeActionPatch({startDate:'',progress:''}),{progress:'',startDate:''});
 assert.equal(normalizeActionImports([{sourceKey:'manual',title:'Sécuriser',startDate:'2026-11-16',dueDate:'2026-11-17',progress:0}])[0].progress,0);
 for(const patch of [{startDate:'2026-02-30'},{startDate:'2026-11-18',dueDate:'2026-11-17'},{progress:101},{progress:-1},{progress:5.5},{progress:'25'}])assert.throws(()=>normalizeActionPatch(patch));
});
