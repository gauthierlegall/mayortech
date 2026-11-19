import test from 'node:test';
import assert from 'node:assert/strict';
import * as preview from './project-notes-preview.mjs';

const native={id:'native-note',source_id:'native-source',origin:'manual_affine',content:'Titre humain\n\n| Intitulé |\n| Action |\n\nObservation après la base'};
const sources=[{id:'native-source',metadata:{remote_id:'affine:page-1'}}];
const projection={status:'ready',pageId:'page-1',fullText:native.content,text:'Titre humain\n\nObservation après la base'};

test('native preview uses the exact page binding and matching full export, without altering stored notes',()=>{
 const original=structuredClone(native),result=preview.projectNotesPreview([native],sources,projection);
 assert.equal(result.notes[0].content,'Titre humain\n\nObservation après la base');
 assert.equal(result.status,'ready');assert.deepEqual(native,original);
});

test('human notes including tables, headings and a note equal to the project title remain intact',()=>{
 const human={...native,id:'human',origin:'human'},title={...human,id:'title',content:'Titre du chantier'};
 assert.deepEqual(preview.projectNotesPreview([human,title],sources,projection).notes,[human,title]);
});

test('a stale or incorrectly bound projection never hides native human content',()=>{
 for(const changed of [{...projection,pageId:'another-page'},{...projection,fullText:'stale full export'}]){
  const result=preview.projectNotesPreview([native],sources,changed);
  assert.equal(result.notes[0].content,native.content);assert.equal(result.status,'unavailable');
 }
});

test('loading defers raw native tables but keeps independent human notes and reports loading',()=>{
 const human={...native,id:'human',origin:'human',content:'Note humaine indépendante'};
 const result=preview.projectNotesPreview([human,native],sources,{status:'loading'});
 assert.deepEqual(result.notes,[human]);assert.equal(result.status,'loading');
});

test('SDK failure preserves all saved text with an explicit unavailable status',()=>{
 const result=preview.projectNotesPreview([native],sources,{status:'unavailable'});
 assert.equal(result.notes[0].content,native.content);assert.equal(result.status,'unavailable');
});

test('a valid empty notes projection says actions-only rather than fabricating missing notes',()=>{
 const result=preview.projectNotesPreview([native],sources,{...projection,text:''});
 assert.equal(result.notes[0].actionsOnly,true);assert.equal(result.status,'ready');
});
