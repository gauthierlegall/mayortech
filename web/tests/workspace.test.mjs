import test from 'node:test';
import assert from 'node:assert/strict';
import {actionInputs, workspaceView} from '../workspace-model.js';

test('confirmed mail actions have a stable source binding and an internal evidence link',()=>{
  const result=actionInputs([{id:'candidate-1',value:{title:'Confirmer les accès',assignee:'Service travaux',due_date:'2026-11-20'},citations:[{source_id:'mail-1'}]}]);
  assert.equal(result[0].sourceKey,'candidate-1');
  assert.equal(result[0].sourceUrl,'#/mail/mail-1');
  assert.equal(result[0].owner,'Service travaux');
  assert.equal(result[0].title,'Confirmer les accès');
});

test('repeated candidates cannot create two imports and malformed entries are skipped',()=>{
  const actions=[{id:'same',value:'Relire le devis'},{id:'same',value:'Relire le devis'},null,{value:'Sans identité'},{id:'empty',value:''}];
  assert.deepEqual(actionInputs(actions).map(item=>item.sourceKey),['same']);
});

test('only supported workspace views are accepted from the URL',()=>{
  assert.equal(workspaceView('kanban'),'kanban');
  assert.equal(workspaceView('documents'),'documents');
  assert.equal(workspaceView('javascript:alert(1)'),'page');
});

test('a long confirmed action and a natural-language deadline do not break the document',()=>{
  const title='A'.repeat(650);
  const [item]=actionInputs([{id:'long',value:{title,due_date:'vendredi prochain'}}]);
  assert.ok(item.title.length<=500);
  assert.ok(item.description.includes(title));
  assert.ok(item.description.includes('vendredi prochain'));
  assert.equal(item.dueDate,'');
});

test('a nonexistent calendar date stays in the description instead of becoming a different date',()=>{
  const [item]=actionInputs([{id:'date',value:{title:'Préparer la visite',due_date:'2026-02-30'}}]);
  assert.equal(item.dueDate,'');
  assert.ok(item.description.includes('2026-02-30'));
});
