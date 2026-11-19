import test from 'node:test';
import assert from 'node:assert/strict';
import * as preview from '../src/notes-preview.mjs';

const snapshot=()=>({id:'doc',blocks:{id:'page',flavour:'affine:page',props:{title:'Titre du dossier'},children:[{id:'note',flavour:'affine:note',props:{},children:[{id:'before',flavour:'affine:paragraph',props:{type:'h1',text:'Titre humain avant la base'},children:[]},{id:'actions',flavour:'affine:database',props:{title:'Actions'},children:[{id:'row',flavour:'affine:paragraph',props:{text:'Action de la base'},children:[]}]},{id:'human-table',flavour:'affine:database',props:{title:'Actions'},children:[{id:'human-row',flavour:'affine:paragraph',props:{text:'Table humaine volontaire, même titre'},children:[]}]},{id:'after',flavour:'affine:paragraph',props:{text:'Observation humaine après la base'},children:[]}]}]}});
function freeze(value){if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}

test('notes projection excludes only the marked database and preserves surrounding human blocks',()=>{
 const original=freeze(snapshot()),fullBefore=JSON.stringify(original);
 const projected=preview.notesSnapshot(original,'actions');
 const children=projected.blocks.children[0].children;
 assert.deepEqual(children.map(block=>block.id),['before','human-table','after']);
 assert.equal(children[0].props.text,'Titre humain avant la base');
 assert.equal(children[1].children[0].props.text,'Table humaine volontaire, même titre');
 assert.equal(children[2].props.text,'Observation humaine après la base');
 assert.equal(JSON.stringify(original),fullBefore,'the full export snapshot remains unchanged');
});

test('missing marker or a marker pointing at a paragraph never removes human content',()=>{
 const original=snapshot();
 for(const marker of [null,undefined,'missing','before'])assert.deepEqual(preview.notesSnapshot(original,marker),original);
});

test('presentation normalization cannot mutate the input snapshot props',()=>{
 const original=freeze(snapshot());
 const projected=preview.notesSnapshot(original,'actions');
 projected.blocks.children[0].children[1].props.title='Titre de présentation';
 assert.equal(original.blocks.children[0].children[2].props.title,'Actions');
});
