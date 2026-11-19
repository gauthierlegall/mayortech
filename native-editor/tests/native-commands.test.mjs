import test from 'node:test';
import assert from 'node:assert/strict';
import {blockSpec, mergeStatusOptions, normalizeActionImports, partitionActionImports, freezeSnapshot} from '../src/native-commands.mjs';

test('visible block commands map to native paragraph/list/divider schemas', () => {
  assert.deepEqual(blockSpec('titre1'), {flavour: 'affine:paragraph', type: 'h1'});
  assert.deepEqual(blockSpec('h2'), {flavour: 'affine:paragraph', type: 'h2'});
  assert.deepEqual(blockSpec('liste'), {flavour: 'affine:list', type: 'bulleted'});
  assert.deepEqual(blockSpec('checkbox'), {flavour: 'affine:list', type: 'todo'});
  assert.deepEqual(blockSpec('citation'), {flavour: 'affine:paragraph', type: 'quote'});
  assert.deepEqual(blockSpec('divider'), {flavour: 'affine:divider'});
  assert.throws(() => blockSpec('html'), /invalid_block_kind/);
});

test('status options preserve human IDs and custom options while adding missing groups once', () => {
  const original = Object.freeze([Object.freeze({id: 'human-in-progress', value: 'En cours', color: '#f00'}), Object.freeze({id: 'travaux-todo', value: 'Validation DSI', color: '#fff'})]);
  const result = mergeStatusOptions(original);
  assert.deepEqual(result.slice(0, 2), original);
  assert.equal(result.filter(option => option.value === 'En cours').length, 1);
  assert.deepEqual(['À faire', 'En cours', 'En attente', 'Terminé'].map(label => result.some(option => option.value === label)), [true, true, true, true]);
  assert.equal(new Set(result.map(option => option.id)).size, result.length);
  assert.deepEqual(mergeStatusOptions(result), result);
});

test('action import accepts bounded canonical mail links and valid calendar dates', () => {
  assert.equal(normalizeActionImports([{sourceKey: 'candidate-1', title: ' Visite de cour ', sourceUrl: '#/mail/source-1', dueDate: '2026-11-18'}])[0].title, 'Visite de cour');
  for (const action of [{sourceKey: 'x', title: ''}, {sourceKey: 'x', title: 'x', sourceUrl: 'https://external.invalid/mail'}, {sourceKey: 'x', title: 'x', dueDate: '2026-02-31'}]) assert.throws(() => normalizeActionImports([action]), /invalid_action_import/);
  assert.throws(() => normalizeActionImports(Array.from({length: 101}, () => ({sourceKey: 'x', title: 'x'}))), /action_import_limit/);
});

test('binding partition never overwrites existing human rows or resurrects deleted rows', () => {
  const actions = normalizeActionImports([{sourceKey: 'existing', title: 'Changed upstream title'}, {sourceKey: 'removed', title: 'Do not resurrect'}, {sourceKey: 'new', title: 'New action'}, {sourceKey: 'new', title: 'Duplicate'}]);
  const bindings = new Map([['existing', {databaseId: 'db', rowId: 'row-kept'}], ['removed', {databaseId: 'db', rowId: 'row-deleted'}]]);
  const result = partitionActionImports(actions, bindings, id => id === 'row-kept');
  assert.deepEqual(result.create.map(action => action.sourceKey), ['new']);
  assert.deepEqual(result.existing, [{sourceKey: 'existing', databaseId: 'db', rowId: 'row-kept'}]);
  assert.deepEqual(result.deleted, [{sourceKey: 'removed', databaseId: 'db', rowId: 'row-deleted'}]);
  assert.deepEqual(result.duplicates, ['new']);
});

test('metadata snapshots are recursively read-only', () => {
  const value = freezeSnapshot({databases: [{rows: [{id: 'native-row'}]}]});
  assert.ok(Object.isFrozen(value) && Object.isFrozen(value.databases) && Object.isFrozen(value.databases[0].rows[0]));
  assert.throws(() => value.databases[0].rows[0].id = 'other', TypeError);
});
